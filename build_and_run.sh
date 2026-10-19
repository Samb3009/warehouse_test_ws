#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
mkdir -p "$HOME/ros2_ws/src"
cp -r warehouse_description warehouse_bringup warehouse_navigation warehouse_battery warehouse_vision "$HOME/ros2_ws/src/"
cd "$HOME/ros2_ws"
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 launch warehouse_bringup warehouse.launch.py
