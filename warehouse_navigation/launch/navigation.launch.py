from launch import LaunchDescription
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution


def generate_launch_description():
    params = PathJoinSubstitution([FindPackageShare('warehouse_navigation'), 'config', 'nav2_params.yaml'])
    map_yaml = PathJoinSubstitution([FindPackageShare('warehouse_navigation'), 'maps', 'warehouse_map.yaml'])
    return LaunchDescription([
        Node(package='nav2_map_server', executable='map_server', name='map_server',
             output='screen', parameters=[params, {'yaml_filename': map_yaml}]),
        Node(package='nav2_amcl', executable='amcl', name='amcl', output='screen', parameters=[params]),
        Node(package='nav2_controller', executable='controller_server', name='controller_server',
             output='screen', parameters=[params], remappings=[('cmd_vel', '/cmd_vel')]),
        Node(package='nav2_planner', executable='planner_server', name='planner_server',
             output='screen', parameters=[params]),
        Node(package='nav2_behaviors', executable='behavior_server', name='behavior_server',
             output='screen', parameters=[params], remappings=[('cmd_vel', '/cmd_vel')]),
        Node(package='nav2_bt_navigator', executable='bt_navigator', name='bt_navigator',
             output='screen', parameters=[params]),
        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager', name='lifecycle_manager_navigation',
             output='screen', parameters=[params]),
    ])
