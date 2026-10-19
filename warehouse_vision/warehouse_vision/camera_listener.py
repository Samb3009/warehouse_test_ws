import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2


class CameraListener(Node):
    def __init__(self):
        super().__init__('camera_listener')
        self.bridge = CvBridge()
        self.count = 0
        self.sub = self.create_subscription(
            Image, '/camera/image_raw', self.callback, 10
        )
        self.get_logger().info('CV handoff ready: subscribed to /camera/image_raw')

    def callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        self.count += 1

        if self.count % 20 == 0:
            h, w = frame.shape[:2]
            self.get_logger().info(f'Camera frame received: {w}x{h}')

        # FRIEND STARTS HERE:
        # Example:
        # results = yolo_model(frame)
        # then publish detections / package IDs / bounding boxes.

        # Keep OpenCV available so a simple sanity check can be added:
        _gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


def main(args=None):
    rclpy.init(args=args)
    node = CameraListener()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
