# Intelligent Autonomous Warehouse Robot

Final-year project simulation architecture combining ROS 2, Gazebo, computer vision, navigation, battery simulation and data-driven task selection.

## Important compatibility note

This variant is adapted for your previously working **Ubuntu 24.04 + ROS 2 Jazzy + Gazebo Sim 8** workspace. It uses the Gazebo Sim 8 plugin names (`gz::sim::systems::*`, `libgz-sim-*-system.so`) and `gz.msgs.*` bridge message types. Do not mix it with a Humble/Fortress installation.

## What was found in the supplied project

The supplied robot has:
- 0.65 m x 0.50 m mobile base
- approximately 18 kg base mass in the URDF
- differential drive
- two driven wheels and a rear/front caster arrangement
- RGB camera at the front of the base
- 2D LiDAR
- IMU
- ROS/Gazebo interfaces for `/cmd_vel`, `/scan`, `/camera/image_raw`, `/camera/camera_info`, `/imu` and `/odom`
- battery simulation node

The supplied robot **does not contain a gripper/manipulator and does not specify an actuator payload rating**. Therefore the box dimensions and weights below are conservative simulation design values, not a claim about real hardware payload capability.

A small front pickup tray was added to the robot model to make the pickup approach geometry explicit. The `warehouse_manipulation` package provides a simulation-only carry/placement interface using Gazebo's `set_pose` service. For a physical robot, this package should later be replaced by the real gripper controller.

## New architecture

```text
                         +----------------------+
                         |   Gazebo Warehouse    |
                         | racks / boxes / zones |
                         +----------+-----------+
                                    |
                           /camera/image_raw
                                    |
                                    v
                         +----------------------+
                         | warehouse_vision     |
                         | QR box-ID detector   |
                         +----------+-----------+
                                    |
                         /warehouse/box_detection
                                    |
                                    v
+----------------+         +----------------------+
| box_database   |-------->| warehouse_decision   |
| YAML metadata  |         | priority/distance/   |
+----------------+         | battery/weight logic |
                           +----------+-----------+
                                      |
                        NavigateToPose / pickup request
                                      |
                 +--------------------+-------------------+
                 |                                        |
                 v                                        v
          +-------------+                         +---------------+
          |    Nav2     |                         | manipulation  |
          | AMCL/planner|                         | pickup/place  |
          +------+------+                         +-------+-------+
                 |                                        |
                 +--------------------+-------------------+
                                      |
                                  robot / Gazebo
```

## Packages

Existing packages retained:
- `warehouse_description`
- `warehouse_bringup`
- `warehouse_navigation`
- `warehouse_battery`
- `warehouse_vision`

New packages:
- `warehouse_environment` — realistic warehouse world, racks, lighting, boxes, labels and destination zones.
- `warehouse_database` — YAML box/destination database and Python loader.
- `warehouse_decision` — task selection and Nav2 decision engine.
- `warehouse_manipulation` — simulation-only pickup/place interface isolated behind ROS topics.

## Warehouse environment

The new world contains:
- approximately 18 x 15 m warehouse floor
- four boundary walls
- three rack banks with posts, shelves and top beams
- multiple overhead lights
- safety barriers
- eight packages: IDs 101–108
- Zone A, Zone B and Zone C
- charging station
- pickup/loading zone

Each package is:
- 0.45 x 0.35 x 0.30 m
- 0.4–0.7 kg according to the database
- positioned on the accessible front side of a rack
- labelled with large `BOX 101`, `BOX 102`, etc.
- labelled with a QR code containing the same numerical ID

The QR code is used for machine detection because it is more reliable than OCR for a rendered Gazebo label, while the large numerical ID remains visible for the project demonstration.

## Box database

File:

```text
warehouse_database/config/box_database.yaml
```

Example entry:

```yaml
103:
  priority: 5
  destination: Zone_C
  weight: 0.45
  type: fragile
  pickup_pose: [-4.0, 1.65, 1.5708]
```

Destinations are real coordinates in the Gazebo world:

```text
Zone_A              (-6.0, -5.0)
Zone_B              ( 0.0, -5.0)
Zone_C              ( 6.0, -5.0)
Charging_Station    (-6.0, -5.8)
Pickup_Loading_Zone ( 0.0, -5.8)
```

## Computer vision

Node:

```text
warehouse_vision/warehouse_vision/box_id_detector.py
```

Input:

```text
/camera/image_raw
```

Outputs:

```text
/warehouse/box_detection
/warehouse/vision/annotated
```

The detection message is JSON carried in `std_msgs/String`, for example:

```json
{"id": 103, "source": "qr", "confidence": 1.0}
```

OpenCV's `QRCodeDetector` performs the ID decoding. The generated label images were tested offline and decode all IDs 101–108.

## Decision making

Node:

```text
warehouse_decision/warehouse_decision/decision_engine.py
```

The task score combines:
- priority
- distance to pickup
- box weight
- battery state
- pending/completed task state

The decision engine can:
- select a pending box
- navigate to its pickup pose
- wait for camera confirmation
- request pickup
- navigate to the destination
- request placement
- mark the task complete
- select the next pending task
- route to the charging station when battery is low
- publish a `REPLAN_REQUIRED` event if a higher-priority box is detected

The heuristic is intentionally transparent so it can be explained during a final-year project presentation and later replaced by an optimizer/ML model.

## Pickup / placement

Because the supplied robot has no gripper, true physical grasping cannot be validated from the supplied project. The simulation interface uses Gazebo's UserCommands `set_pose` service to keep the selected box at the front pickup tray while the robot moves, then moves the box into its destination zone during placement.

ROS interface:

```text
/warehouse/pickup_request
/warehouse/pickup_status
```

This isolates the manipulation layer so a real gripper controller can later subscribe to the same request and publish the same status.

## Install dependencies — Jazzy

```bash
sudo apt update
sudo apt install -y \
  ros-jazzy-xacro \
  ros-jazzy-robot-state-publisher \
  ros-jazzy-joint-state-publisher \
  ros-jazzy-ros-gz-sim \
  ros-jazzy-ros-gz-bridge \
  ros-jazzy-slam-toolbox \
  ros-jazzy-navigation2 \
  ros-jazzy-nav2-bringup \
  ros-jazzy-nav2-map-server \
  ros-jazzy-nav2-amcl \
  ros-jazzy-nav2-controller \
  ros-jazzy-nav2-planner \
  ros-jazzy-nav2-behaviors \
  ros-jazzy-nav2-bt-navigator \
  ros-jazzy-nav2-lifecycle-manager \
  ros-jazzy-cv-bridge \
  ros-jazzy-rqt-image-view \
  python3-opencv \
  python3-yaml
```

## Build

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

## Launch the complete demonstration

### Option A — one command

```bash
ros2 launch warehouse_bringup demo.launch.py
```

The launch sequence starts the warehouse first, then Nav2, then the vision/decision/pickup stack.

### Option B — separate terminals

Terminal 1 — warehouse + robot:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch warehouse_bringup warehouse.launch.py
```

Keep this terminal running.

Terminal 2 — navigation:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch warehouse_navigation navigation.launch.py
```

Keep this terminal running.

Terminal 3 — automation:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch warehouse_bringup automation.launch.py
```

Keep this terminal running.

## Camera test

```bash
ros2 run rqt_image_view rqt_image_view
```

Select:

```text
/camera/image_raw
```

To see the annotated detection stream, select:

```text
/warehouse/vision/annotated
```

## Test box-ID detection separately

```bash
ros2 run warehouse_vision box_id_detector
```

Then move the robot so a labelled box is in the camera view.

Check:

```bash
ros2 topic echo /warehouse/box_detection
```

## Test the decision stream

```bash
ros2 topic echo /warehouse/decision
```

## Test pickup interface manually

At the correct pickup pose:

```bash
ros2 topic pub --once /warehouse/pickup_request std_msgs/msg/String \
"{data: '{\"id\":103,\"action\":\"pick\"}'}"
```

Then place:

```bash
ros2 topic pub --once /warehouse/pickup_request std_msgs/msg/String \
"{data: '{\"id\":103,\"action\":\"place\"}'}"
```

## Adding a new box

1. Add a new label image under `warehouse_environment/textures/`.
2. Add the box model to `warehouse_environment/worlds/warehouse.sdf`.
3. Add the matching ID and metadata to `warehouse_database/config/box_database.yaml`.
4. Add its pickup pose and destination.
5. Rebuild and source the workspace.

## Changing priority or destination

Edit only:

```text
warehouse_database/config/box_database.yaml
```

For example, changing:

```yaml
priority: 5
destination: Zone_C
```

changes the information used by the decision engine without changing the vision node.

## Important limitation

The simulation demonstrates the complete software flow and a simulation-only pickup abstraction, but it does **not** prove a real hardware gripper payload or grasping capability because those mechanisms are absent from the supplied robot model. For a physical deployment, replace `warehouse_manipulation` with the actual gripper/arm controller and validate payload, reach, clearance and grasp stability experimentally.
