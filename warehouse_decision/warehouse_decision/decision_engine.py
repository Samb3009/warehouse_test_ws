import json
import math

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry
from sensor_msgs.msg import BatteryState
from std_msgs.msg import String

from warehouse_database import load_database


class DecisionEngine(Node):
    def __init__(self):
        super().__init__('warehouse_decision_engine')
        self.db = load_database()
        self.pending = set(self.db['boxes'].keys())
        self.completed = set()
        self.current = None
        self.state = 'SELECT_TASK'
        self.x = self.y = 0.0
        self.battery = 1.0
        self.action_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.det_sub = self.create_subscription(String, '/warehouse/box_detection', self.detection_cb, 10)
        self.pick_sub = self.create_subscription(String, '/warehouse/pickup_status', self.pick_status_cb, 10)
        self.odom_sub = self.create_subscription(Odometry, '/odom', self.odom_cb, 10)
        self.batt_sub = self.create_subscription(BatteryState, '/battery_state', self.battery_cb, 10)
        self.pick_pub = self.create_publisher(String, '/warehouse/pickup_request', 10)
        self.status_pub = self.create_publisher(String, '/warehouse/decision', 10)
        self.timer = self.create_timer(1.0, self.tick)
        self.get_logger().info('Decision engine started: priority + distance + battery + weight')

    def odom_cb(self, msg):
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y

    def battery_cb(self, msg):
        if msg.percentage > 1.0:
            self.battery = msg.percentage / 100.0
        else:
            self.battery = msg.percentage

    def publish(self, data):
        m = String(); m.data = json.dumps(data); self.status_pub.publish(m)

    def score(self, box_id):
        b = self.db['boxes'][box_id]
        px, py, _ = b['pickup_pose']
        distance = math.hypot(self.x - px, self.y - py)
        # Transparent, deterministic heuristic suitable for a final-year demo.
        return 10.0 * b['priority'] - 0.8 * distance - 2.0 * b['weight']

    def choose_task(self):
        if not self.pending:
            return None
        return max(self.pending, key=self.score)

    def send_goal(self, x, y, yaw, label):
        if not self.action_client.wait_for_server(timeout_sec=2.0):
            self.get_logger().warning('Nav2 action server not available yet.')
            return False
        goal = NavigateToPose.Goal()
        goal.pose = PoseStamped()
        goal.pose.header.frame_id = 'map'
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = float(x)
        goal.pose.pose.position.y = float(y)
        goal.pose.pose.orientation.z = math.sin(float(yaw) / 2.0)
        goal.pose.pose.orientation.w = math.cos(float(yaw) / 2.0)
        future = self.action_client.send_goal_async(goal)
        future.add_done_callback(lambda f: self.goal_response_cb(f, label))
        return True

    def goal_response_cb(self, future, label):
        try:
            handle = future.result()
            if not handle.accepted:
                self.get_logger().warning(f'Navigation goal rejected: {label}')
                return
            self.get_logger().info(f'Navigation goal accepted: {label}')
            result_future = handle.get_result_async()
            result_future.add_done_callback(lambda f: self.goal_result_cb(f, label))
        except Exception as exc:
            self.get_logger().warning(f'Navigation action error: {exc}')

    def goal_result_cb(self, future, label):
        try:
            status = future.result().status
            self.get_logger().info(f'Navigation completed for {label}, status={status}')
            if label == 'pickup' and self.current is not None:
                self.state = 'WAIT_FOR_ID'
                self.publish({'state': self.state, 'box': self.current, 'reason': 'at_pickup_pose'})
            elif label == 'destination' and self.current is not None:
                req = String(); req.data = json.dumps({'id': self.current, 'action': 'place'})
                self.pick_pub.publish(req)
                self.state = 'WAIT_FOR_PLACE'
            elif label == 'charge':
                self.state = 'SELECT_TASK'
        except Exception:
            pass

    def detection_cb(self, msg):
        try:
            data = json.loads(msg.data)
            detected = int(data['id'])
        except Exception:
            return
        if detected not in self.db['boxes'] or detected in self.completed:
            return
        if self.current is None:
            return
        current_priority = self.db['boxes'][self.current]['priority']
        detected_priority = self.db['boxes'][detected]['priority']
        if self.state == 'WAIT_FOR_ID' and detected == self.current:
            req = String(); req.data = json.dumps({'id': detected, 'action': 'pick'})
            self.pick_pub.publish(req)
            self.state = 'WAIT_FOR_PICK'
            self.publish({'state': self.state, 'box': detected, 'reason': 'camera_confirmed_id'})
        elif detected != self.current and detected_priority > current_priority:
            # Decision layer records the better task; the current navigation goal is allowed to finish safely.
            self.pending.add(detected)
            self.publish({'state': 'REPLAN_REQUIRED', 'current_box': self.current,
                          'detected_box': detected, 'reason': 'higher_priority_box_detected'})

    def pick_status_cb(self, msg):
        try:
            data = json.loads(msg.data)
            box_id = int(data['id'])
            status = data['status']
        except Exception:
            return
        if box_id != self.current:
            return
        if status == 'picked':
            dest = self.db['boxes'][box_id]['destination']
            x, y, yaw = self.db['destinations'][dest]
            self.state = 'DELIVERING'
            self.publish({'state': self.state, 'box': box_id, 'destination': dest,
                          'priority': self.db['boxes'][box_id]['priority'],
                          'weight': self.db['boxes'][box_id]['weight']})
            self.send_goal(x, y, yaw, 'destination')
        elif status == 'placed':
            self.completed.add(box_id)
            self.pending.discard(box_id)
            self.current = None
            self.state = 'SELECT_TASK'
            self.publish({'state': self.state, 'completed_box': box_id, 'remaining': len(self.pending)})

    def tick(self):
        if self.state == 'SELECT_TASK':
            if self.battery < 0.25 and math.hypot(self.x + 6.0, self.y + 5.8) > 1.5:
                self.state = 'CHARGING'
                self.publish({'state': self.state, 'battery': self.battery, 'reason': 'battery_low'})
                self.send_goal(*self.db['destinations']['Charging_Station'], 'charge')
                return
            if self.current is None:
                self.current = self.choose_task()
                if self.current is None:
                    self.state = 'IDLE'
                    self.publish({'state': self.state, 'reason': 'all_tasks_complete'})
                    return
                b = self.db['boxes'][self.current]
                self.publish({'state': 'NAVIGATE_TO_PICKUP', 'box': self.current,
                              'priority': b['priority'], 'destination': b['destination'],
                              'weight': b['weight'], 'score': round(self.score(self.current), 2),
                              'battery': round(self.battery, 3)})
                self.state = 'NAVIGATING_PICKUP'
                self.send_goal(*b['pickup_pose'], 'pickup')


def main(args=None):
    rclpy.init(args=args)
    node = DecisionEngine()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
