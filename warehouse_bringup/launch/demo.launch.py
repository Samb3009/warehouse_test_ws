from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    bringup = FindPackageShare('warehouse_bringup')
    navigation = FindPackageShare('warehouse_navigation')
    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([bringup, 'launch', 'warehouse.launch.py']))
        ),
        TimerAction(
            period=8.0,
            actions=[IncludeLaunchDescription(
                PythonLaunchDescriptionSource(PathJoinSubstitution([navigation, 'launch', 'navigation.launch.py']))
            )]
        ),
        TimerAction(
            period=15.0,
            actions=[IncludeLaunchDescription(
                PythonLaunchDescriptionSource(PathJoinSubstitution([bringup, 'launch', 'automation.launch.py']))
            )]
        ),
    ])
