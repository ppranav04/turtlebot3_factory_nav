"""Simulated CNC stations: fill a finished-parts box, ask for pickup when full."""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from turtlebot3_factory_interfaces.msg import PickupRequest
import yaml


class StationSim(Node):
    """Count parts into each station's box and request a pickup at capacity."""

    def __init__(self):
        super().__init__('station_sim')
        self.declare_parameter('stations_file', '')
        path = self.get_parameter('stations_file').value
        if not path:
            raise RuntimeError('station_sim needs the stations_file parameter')
        with open(path) as f:
            config = yaml.safe_load(f)

        self.capacity = config['capacity']
        self.fill = {sid: 0 for sid in config['stations']}
        self.max_fills = config.get('fills_per_station', 0)
        self.fills = {sid: 0 for sid in config['stations']}

        self.pub = self.create_publisher(PickupRequest, 'pickup_request', 10)
        self.create_subscription(String, 'station_done', self.on_done, 10)

        for sid, station in config['stations'].items():
            self.create_timer(station['seconds_per_part'],
                              lambda sid=sid: self.on_part(sid))

        self.create_timer(2.0, self.republish)
        self.get_logger().info(
            f'{len(self.fill)} stations, capacity {self.capacity}, file {path}')

    def on_part(self, sid):
        if self.max_fills and self.fills[sid] >= self.max_fills:
            return
        if self.fill[sid] >= self.capacity:
            return
        self.fill[sid] += 1
        self.get_logger().debug(f'Station {sid}: {self.fill[sid]}/{self.capacity}')
        if self.fill[sid] == self.capacity:
            self.fills[sid] += 1
            self.get_logger().info(f'Station {sid}: box full, requesting pickup')
            self.request(sid)

    def request(self, sid):
        msg = PickupRequest()
        msg.station_id = sid
        msg.fill_level = self.fill[sid]
        msg.capacity = self.capacity
        msg.stamp = self.get_clock().now().to_msg()
        self.pub.publish(msg)

    def republish(self):
        for sid, count in self.fill.items():
            if count >= self.capacity:
                self.request(sid)

    def on_done(self, msg):
        if msg.data in self.fill:
            self.fill[msg.data] = 0
            self.get_logger().info(f'Station {msg.data}: box collected, refilling')


def main(args=None):
    rclpy.init(args=args)
    node = StationSim()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
