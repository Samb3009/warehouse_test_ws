import json
import math
import shutil
import subprocess

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from std_msgs.msg import String

from warehouse_database import load_database


class PickupManager(Node):
    """Simulation pickup interface.

    The supplied robot has no physical gripper. This node therefore uses Gazebo's
    UserCommands set_pose service to keep a selected box at the robot's front
    pickup tray while carrying it. This is intentionally isolated so a real
    gripper controller can replace it later without changing the decision layer.
    """
    def __init__(self):
        super().__init__('pickup_manager')
        self.db = load_database()
        self.x = self.y = 0.0
        self.yaw = 0.0
        self.carrying = None
        self.cmd_sub = self.create_subscription(String, '/warehouse/pickup_request', self.request_cb, 10)
        self.odom_sub = self.create_subscription(Odometry, '/odom', self.odom_cb, 10)
        self.status_pub = self.create_publisher(String, '/warehouse/pickup_status', 10)
        self.timer = self.create_timer(0.25, self.carry_update)
        self.cli = shutil.which('gz') or shutil.which('ign')
        self.msg_type = 'gz.msgs.Pose' if self.cli and self.cli.endswith('/gz') else 'ignition.msgs.Pose'
        if not self.cli:
            self.get_logger().warning('Neither gz nor ign CLI was found; pickup will publish simulation status only.')
        else:
            self.get_logger().info(f'Gazebo pose interface: {self.cli}')

    def odom_cb(self, msg):
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y
        q = msg.pose.pose.orientation
        self.yaw = math.atan2(2.0 * (q.w*q.z + q.x*q.y), 1.0 - 2.0 * (q.y*q.y + q.z*q.z))

    def publish(self, data):
        m = String(); m.data = json.dumps(data); self.status_pub.publish(m)

    def set_pose(self, model_name, x, y, z, yaw):
        if not self.cli:
            return False
        req = (f"name: '{model_name}' position: {{x: {x:.3f}, y: {y:.3f}, z: {z:.3f}}} "
               f"orientation: {{x: 0, y: 0, z: {math.sin(yaw/2):.6f}, w: {math.cos(yaw/2):.6f}}}")
        cmd = [self.cli, 'service', '-s', '/world/warehouse/set_pose',
               '--reqtype', self.msg_type, '--reptype',
               'gz.msgs.Boolean' if self.msg_type.startswith('gz.') else 'ignition.msgs.Boolean',
               '--req', req, '--timeout', '1000']
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=2.0)
            return result.returncode == 0
        except Exception as exc:
            self.get_logger().warning(f'Gazebo set_pose failed: {exc}')
            return False

    def request_cb(self, msg):
        try:
            req = json.loads(msg.data)
            box_id = int(req['id'])
            action = req.get('action', 'pick')
        except Exception:
            self.get_logger().warning('Invalid pickup request JSON')
            return
        if box_id not in self.db['boxes']:
            self.publish({'id': box_id, 'status': 'failed', 'reason': 'unknown_box'})
            return
        if action == 'pick':
            pose = self.db['boxes'][box_id]['pickup_pose']
            dist = math.hypot(self.x - pose[0], self.y - pose[1])
            if dist > 0.9:
                self.publish({'id': box_id, 'status': 'failed', 'reason': f'not_at_pickup_distance_{dist:.2f}'})
                return
            self.carrying = box_id
            self.publish({'id': box_id, 'status': 'picked', 'mode': 'simulation_tray'})
            self.get_logger().info(f'Picked box {box_id} using simulation tray interface.')
        elif action == 'place':
            if self.carrying != box_id:
                self.publish({'id': box_id, 'status': 'failed', 'reason': 'not_carrying'})
                return
            dest = self.db['boxes'][box_id]['destination']
            x, y, yaw = self.db['destinations'][dest]
            self.set_pose(f'box_{box_id}', x, y, 0.20, yaw)
            self.carrying = None
            self.publish({'id': box_id, 'status': 'placed', 'destination': dest})
            self.get_logger().info(f'Placed box {box_id} at {dest}.')

    def carry_update(self):
        if self.carrying is None:
            return
        front = 0.55
        x = self.x + front * math.cos(self.yaw)
        y = self.y + front * math.sin(self.yaw)
        self.set_pose(f'box_{self.carrying}', x, y, 0.23, self.yaw)


def main(args=None):
    rclpy.init(args=args)
    node = PickupManager()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
