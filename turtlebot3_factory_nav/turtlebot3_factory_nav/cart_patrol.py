"""
Move the pallet cart back and forth across the dock zone with set_pose.

The cart pauses while the robot is within a clearance distance, like a
powered cart with its own safety scanner.
"""

import math

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from ros_gz_interfaces.msg import Entity
from ros_gz_interfaces.srv import SetEntityPose
from tf2_ros import Buffer, TransformException, TransformListener


class CartPatrol(Node):
    """Teleport the cart along y; pause at each end and while the robot is close."""

    def __init__(self):
        super().__init__('cart_patrol')
        self.declare_parameter('world', 'factory_floor')
        self.declare_parameter('model', 'cart')
        self.declare_parameter('x', 1.1)
        self.declare_parameter('y_start', 1.1)
        self.declare_parameter('y_end', -1.1)
        self.declare_parameter('speed', 0.12)
        self.declare_parameter('dwell', 4.0)
        self.declare_parameter('rate', 20.0)
        self.declare_parameter('clearance', 0.75)

        world = self.get_parameter('world').value
        self.model = self.get_parameter('model').value
        self.x = self.get_parameter('x').value
        self.y_start = self.get_parameter('y_start').value
        self.y_end = self.get_parameter('y_end').value
        self.speed = self.get_parameter('speed').value
        self.dwell = self.get_parameter('dwell').value
        rate = self.get_parameter('rate').value
        self.clearance = self.get_parameter('clearance').value

        self.client = self.create_client(SetEntityPose, f'/world/{world}/set_pose')
        self.pending = None
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.tp = 0.0
        self.last = None
        self.blocked = False
        self.timer = self.create_timer(1.0 / rate, self.on_timer)
        self.get_logger().info(
            f'Patrolling {self.model} at x={self.x} between y={self.y_start} and '
            f'y={self.y_end}, {self.speed} m/s, {self.dwell} s dwell'
        )

    def position_at(self, t):
        """Return the cart's y at t seconds after the patrol started."""
        travel = abs(self.y_end - self.y_start) / self.speed
        period = 2.0 * (self.dwell + travel)
        t = t % period
        if t < self.dwell:
            return self.y_start
        t -= self.dwell
        if t < travel:
            return self.y_start + (self.y_end - self.y_start) * t / travel
        t -= travel
        if t < self.dwell:
            return self.y_end
        t -= self.dwell
        return self.y_end + (self.y_start - self.y_end) * t / travel

    def robot_too_close(self, y):
        """Return True if the robot is within clearance of the cart at (x, y)."""
        try:
            tf = self.tf_buffer.lookup_transform('map', 'base_footprint', Time())
        except TransformException:
            return False
        dx = tf.transform.translation.x - self.x
        dy = tf.transform.translation.y - y
        return math.hypot(dx, dy) < self.clearance

    def on_timer(self):
        now = self.get_clock().now().nanoseconds * 1e-9
        if now == 0.0 or not self.client.service_is_ready():
            return
        if self.pending is not None and not self.pending.done():
            return
        if self.last is None:
            self.last = now
        dt = now - self.last
        self.last = now
        blocked = self.robot_too_close(self.position_at(self.tp))
        if blocked != self.blocked:
            self.blocked = blocked
            self.get_logger().info(
                'Robot close, cart waiting' if blocked else 'Path clear, cart moving')
        if not blocked:
            self.tp += dt
        req = SetEntityPose.Request()
        req.entity.name = self.model
        req.entity.type = Entity.MODEL
        req.pose.position.x = self.x
        req.pose.position.y = self.position_at(self.tp)
        req.pose.orientation.w = 1.0
        self.pending = self.client.call_async(req)


def main(args=None):
    rclpy.init(args=args)
    node = CartPatrol()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
