"""FIFO pickup dispatcher node: runs dispatcher_logic actions with NAV2 and Gazebo."""

import math

from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from ros_gz_interfaces.msg import Entity
from ros_gz_interfaces.srv import DeleteEntity, SpawnEntity
from std_msgs.msg import String
from turtlebot3_factory_interfaces.msg import PickupRequest
from turtlebot3_factory_nav.dispatcher_logic import (
    Dispatcher, DOCK, NAVIGATE, REMOVE_BOX, SPAWN_BOX, STATION_DONE, STORAGE, WAIT)
import yaml

BOX_SDF = """<?xml version="1.0"?>
<sdf version="1.9">
    <model name="box">
        <static>true</static>
        <link name="link">
        <collision name="c">
            <geometry>
                <box>
                    <size>0.25 0.25 0.15</size>
                </box>
            </geometry>
        </collision>
        <visual name="v">
            <geometry>
                <box>
                    <size>0.25 0.25 0.15</size>
                </box>
            </geometry>
            <material>
                <diffuse>{color}</diffuse>
                <ambient>{color}</ambient>
            </material>
            </visual>
        </link>
    </model>
</sdf>
"""

FULL_COLOR = '0.2 0.4 0.9 1'
EMPTY_COLOR = '0.6 0.6 0.6 1'


def make_pose(frame_id, stamp, x, y, yaw):
    """Build a PoseStamped from x, y and yaw (radians)."""
    pose = PoseStamped()
    pose.header.frame_id = frame_id
    pose.header.stamp = stamp
    pose.pose.position.x = float(x)
    pose.pose.position.y = float(y)
    pose.pose.orientation.z = math.sin(yaw / 2.0)
    pose.pose.orientation.w = math.cos(yaw / 2.0)
    return pose


class TaskDispatcher(Node):
    """Turn pickup requests into Nav2 goals and Gazebo moves."""

    def __init__(self, navigator):
        super().__init__('task_dispatcher')
        self.declare_parameter('stations_file', '')
        self.declare_parameter('world', 'factory_floor')
        path = self.get_parameter('stations_file').value
        if not path:
            raise RuntimeError('task_dispatcher needs the stations_file parameter')
        with open(path) as f:
            self.config = yaml.safe_load(f)
        world = self.get_parameter('world').value

        self.nav = navigator
        self.logic = Dispatcher(dwell_s=self.config['dwell_s'])
        self.navigating = False
        self.dwell_timer = None
        self.stored = 0

        self.done_pub = self.create_publisher(String, 'station_done', 10)
        self.create_subscription(PickupRequest, 'pickup_request', self.on_request, 10)
        self.remove_cli = self.create_client(DeleteEntity, f'/world/{world}/remove')
        self.spawn_cli = self.create_client(SpawnEntity, f'/world/{world}/create')

    def step(self, event, handler, *args):
        """Feed one event to the logic, log what changed, run the actions."""
        before_state, before_queue = self.logic.state, self.logic.queue
        actions = handler(*args)
        if self.logic.state != before_state:
            where = f' [{self.logic.current}]' if self.logic.current else ''
            self.get_logger().info(
                f'{event}: {before_state.value} -> {self.logic.state.value}{where}')
        if self.logic.queue != before_queue:
            self.get_logger().info(f'Queue: {self.logic.queue}')
        for action in actions:
            self.run(action)

    def on_request(self, msg):
        self.step(f'request {msg.station_id}', self.logic.on_request, msg.station_id)

    def on_dwell_timer(self):
        self.dwell_timer.cancel()
        self.destroy_timer(self.dwell_timer)
        self.dwell_timer = None
        self.step('dwell done', self.logic.on_dwell_done)

    def run(self, action):
        if action.kind == NAVIGATE:
            self.navigate(action.arg)
        elif action.kind == WAIT:
            self.get_logger().info(f'Simulated pickup: waiting {action.arg} s')
            self.dwell_timer = self.create_timer(action.arg, self.on_dwell_timer)
        elif action.kind == REMOVE_BOX:
            self.remove_model(f'bin_{action.arg.lower()}')
        elif action.kind == SPAWN_BOX:
            self.stored += 1
            x, y, z = self.config['stations'][action.arg]['slot']
            self.spawn_box(f'stored_{self.stored}', x, y, z, FULL_COLOR)
        elif action.kind == STATION_DONE:
            x, y, z = self.config['stations'][action.arg]['bin']
            self.spawn_box(f'bin_{action.arg.lower()}', x, y, z, EMPTY_COLOR)
            self.done_pub.publish(String(data=action.arg))

    def navigate(self, target):
        if target in (STORAGE, DOCK):
            x, y, yaw = self.config[target]['pose']
        else:
            x, y, yaw = self.config['stations'][target]['pose']
        goal = make_pose('map', self.nav.get_clock().now().to_msg(), x, y, yaw)
        self.get_logger().info(f'Navigating to {target} ({x}, {y})')
        self.nav.goToPose(goal)
        self.navigating = True

    def remove_model(self, name):
        req = DeleteEntity.Request()
        req.entity.name = name
        req.entity.type = Entity.MODEL
        future = self.remove_cli.call_async(req)
        future.add_done_callback(lambda f: self.report(f, f'removed {name}'))

    def spawn_box(self, name, x, y, z, color):
        req = SpawnEntity.Request()
        req.entity_factory.name = name
        req.entity_factory.sdf = BOX_SDF.format(color=color)
        req.entity_factory.pose.position.x = float(x)
        req.entity_factory.pose.position.y = float(y)
        req.entity_factory.pose.position.z = float(z)
        future = self.spawn_cli.call_async(req)
        future.add_done_callback(lambda f: self.report(f, f'spawned {name}'))

    def report(self, future, what):
        result = future.result()
        if result is not None and result.success:
            self.get_logger().info(f'Gazebo: {what}')
        else:
            self.get_logger().warn(f'Gazebo: {what} FAILED')

    def poll_nav(self):
        """Check the running Nav2 goal and feed its result to the logic."""
        if not self.navigating or not self.nav.isTaskComplete():
            return
        self.navigating = False
        result = self.nav.getResult()
        if result == TaskResult.SUCCEEDED:
            self.step('nav succeeded', self.logic.on_nav_succeeded)
        else:
            self.get_logger().warn(f'Navigation ended with {result.name}')
            self.step('nav failed', self.logic.on_nav_failed)


def main(args=None):
    rclpy.init(args=args)
    navigator = BasicNavigator()
    node = TaskDispatcher(navigator)
    x, y, yaw = node.config['dock']['pose']
    navigator.setInitialPose(
        make_pose('map', navigator.get_clock().now().to_msg(), x, y, yaw))
    navigator.waitUntilNav2Active()
    node.get_logger().info('Nav2 active, waiting for pickup requests')
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    try:
        while rclpy.ok():
            executor.spin_once(timeout_sec=0.1)
            node.poll_nav()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        navigator.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
