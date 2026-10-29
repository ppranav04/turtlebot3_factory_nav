"""Move the pallet cart back and forth across the dock zone with set_pose."""

import rclpy
from rclpy.node import Node
from ros_gz_interfaces.msg import Entity
from ros_gz_interfaces.srv import SetEntityPose


class CartPatrol(Node):
    """Teleport a static Gazebo model along y at constant speed, pausing at each end."""

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

        world = self.get_parameter('world').value
        self.model = self.get_parameter('model').value
        self.x = self.get_parameter('x').value
        self.y_start = self.get_parameter('y_start').value
        self.y_end = self.get_parameter('y_end').value
        self.speed = self.get_parameter('speed').value
        self.dwell = self.get_parameter('dwell').value
        rate = self.get_parameter('rate').value

        self.client = self.create_client(SetEntityPose, f'/world/{world}/set_pose')
        self.pending = None
        self.t0 = None
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

    def on_timer(self):
        now = self.get_clock().now().nanoseconds * 1e-9
        if now == 0.0 or not self.client.service_is_ready():
            return
        if self.pending is not None and not self.pending.done():
            return
        if self.t0 is None:
            self.t0 = now
        req = SetEntityPose.Request()
        req.entity.name = self.model
        req.entity.type = Entity.MODEL
        req.pose.position.x = self.x
        req.pose.position.y = self.position_at(now - self.t0)
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
