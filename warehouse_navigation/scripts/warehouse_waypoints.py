#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped


class WarehouseWaypoints(Node):
    def __init__(self):
        super().__init__('warehouse_waypoints')
        self.pub = self.create_publisher(PoseStamped, '/warehouse/waypoint', 10)

        # Useful reference points for your final task planner.
        self.waypoints = [
            ('charging_station', -6.0, -5.2),
            ('rack_A', -5.0, 2.7),
            ('rack_B', 0.0, 2.7),
            ('rack_C', 5.0, 2.7),
            ('rack_D', -5.0, -0.0),
            ('rack_E', 0.0, -0.0),
            ('rack_F', 5.0, -0.0),
            ('dispatch', 6.0, -5.2),
        ]
        self.index = 0
        self.timer = self.create_timer(5.0, self.publish_next)

    def publish_next(self):
        name, x, y = self.waypoints[self.index]
        msg = PoseStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'map'
        msg.pose.position.x = x
        msg.pose.position.y = y
        msg.pose.orientation.w = 1.0
        self.pub.publish(msg)
        self.get_logger().info(f'Waypoint: {name} ({x:.1f}, {y:.1f})')
        self.index = (self.index + 1) % len(self.waypoints)


def main(args=None):
    rclpy.init(args=args)
    node = WarehouseWaypoints()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
