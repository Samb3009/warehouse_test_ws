import json
import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge


class BoxIdDetector(Node):
    def __init__(self):
        super().__init__('box_id_detector')
        self.bridge = CvBridge()
        self.detector = cv2.QRCodeDetector()
        self.last_id = None
        self.pub = self.create_publisher(String, '/warehouse/box_detection', 10)
        self.annotated_pub = self.create_publisher(Image, '/warehouse/vision/annotated', 10)
        self.sub = self.create_subscription(Image, '/camera/image_raw', self.callback, 10)
        self.get_logger().info('Box ID detector ready: QR + visible numerical ID labels')

    def callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        data, points, _ = self.detector.detectAndDecode(frame)
        if not data:
            try:
                ok, decoded, points, _ = self.detector.detectAndDecodeMulti(frame)
                if ok and decoded:
                    data = next((d for d in decoded if d), '')
            except Exception:
                pass

        if data:
            try:
                box_id = int(data.strip())
            except ValueError:
                return
            if box_id < 100 or box_id > 999:
                return
            payload = {'id': box_id, 'source': 'qr', 'confidence': 1.0}
            out = String()
            out.data = json.dumps(payload)
            self.pub.publish(out)
            if box_id != self.last_id:
                self.get_logger().info(f'Detected warehouse box ID: {box_id}')
                self.last_id = box_id
            if points is not None:
                pts = points.reshape(-1, 2).astype(int)
                for i in range(len(pts)):
                    cv2.line(frame, tuple(pts[i]), tuple(pts[(i + 1) % len(pts)]), (0, 255, 0), 3)
                cv2.putText(frame, f'BOX {box_id}', tuple(pts[0]), cv2.FONT_HERSHEY_SIMPLEX,
                            1.0, (0, 255, 0), 2)
        try:
            self.annotated_pub.publish(self.bridge.cv2_to_imgmsg(frame, encoding='bgr8'))
        except Exception:
            pass


def main(args=None):
    rclpy.init(args=args)
    node = BoxIdDetector()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
