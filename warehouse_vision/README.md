# Computer Vision handoff

The robot camera is already mounted and the bridge publishes:

- `/camera/image_raw`
- `/camera/camera_info`

Run:

```bash
ros2 run warehouse_vision camera_listener
```

Your next job is to replace the example callback with YOLO/OpenCV.

Recommended interface:

```text
ROS Image
   ↓
cv_bridge
   ↓
OpenCV frame
   ↓
YOLO
   ↓
Detection result
   ↓
Warehouse manager / Nav2 task
```

Suggested detections:
- package
- pallet
- shelf marker
- human/obstacle
- package color/class

Do not hard-code a real camera file; use `/camera/image_raw` from Gazebo so the same CV node can later work with a real camera.
