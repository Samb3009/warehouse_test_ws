import math
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist
from sensor_msgs.msg import BatteryState


class BatteryManager(Node):
    def __init__(self):
        super().__init__('battery_manager')

        self.level = 100.0
        self.last_time = self.get_clock().now()
        self.v = 0.0
        self.w = 0.0
        self.x = 0.0
        self.y = 0.0

        self.declare_parameter('battery_capacity_ah', 20.0)
        self.declare_parameter('charge_rate_percent_per_second', 0.35)
        self.declare_parameter('idle_drain_percent_per_second', 0.002)
        self.declare_parameter('drive_drain_percent_per_second', 0.025)

        self.sub_odom = self.create_subscription(Odometry, '/odom', self.odom_cb, 10)
        self.sub_cmd = self.create_subscription(Twist, '/cmd_vel', self.cmd_cb, 10)
        self.pub = self.create_publisher(BatteryState, '/battery_state', 10)
        self.timer = self.create_timer(0.5, self.update)

        self.get_logger().info('Battery manager started. Charging zone: x=-6, y=-5.2')

    def odom_cb(self, msg):
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y

    def cmd_cb(self, msg):
        self.v = abs(msg.linear.x)
        self.w = abs(msg.angular.z)

    def in_charging_zone(self):
        return abs(self.x + 6.0) < 1.3 and abs(self.y + 5.2) < 0.9

    def update(self):
        now = self.get_clock().now()
        dt = (now - self.last_time).nanoseconds / 1e9
        self.last_time = now

        if dt <= 0 or dt > 5:
            dt = 0.5

        charging = self.in_charging_zone()

        if charging:
            self.level += self.get_parameter('charge_rate_percent_per_second').value * dt
        else:
            drain = self.get_parameter('idle_drain_percent_per_second').value
            drain += self.get_parameter('drive_drain_percent_per_second').value * self.v
            drain += 0.01 * self.w
            self.level -= drain * dt

        self.level = max(0.0, min(100.0, self.level))

        msg = BatteryState()
        msg.header.stamp = now.to_msg()
        msg.header.frame_id = 'base_link'
        msg.voltage = 24.0 * self.level / 100.0
        msg.current = -(self.v * 2.0 + self.w * 0.5) if not charging else -2.0
        msg.charge = 20.0 * self.level / 100.0
        msg.capacity = 20.0
        msg.design_capacity = 20.0
        msg.percentage = self.level / 100.0
        msg.power_supply_status = (
            BatteryState.POWER_SUPPLY_STATUS_CHARGING
            if charging else BatteryState.POWER_SUPPLY_STATUS_DISCHARGING
        )
        msg.power_supply_health = BatteryState.POWER_SUPPLY_HEALTH_GOOD
        msg.power_supply_technology = BatteryState.POWER_SUPPLY_TECHNOLOGY_LION
        msg.present = True
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = BatteryManager()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
