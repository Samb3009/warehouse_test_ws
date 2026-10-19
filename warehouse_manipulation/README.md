# Simulation pickup interface

The original robot ZIP contains no physical gripper. This package provides a clearly isolated simulation-only pickup interface. When a box is picked, Gazebo's UserCommands `set_pose` service is used to keep the box at the front pickup tray while the robot moves. On placement, the box is moved to the destination zone.

For a real gripper, replace this node with the manipulator/gripper controller while keeping the same `/warehouse/pickup_request` and `/warehouse/pickup_status` interface.
