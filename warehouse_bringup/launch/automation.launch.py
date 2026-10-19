from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(package='warehouse_vision', executable='box_id_detector', name='box_id_detector', output='screen'),
        Node(package='warehouse_manipulation', executable='pickup_manager', name='pickup_manager', output='screen'),
        Node(package='warehouse_decision', executable='decision_engine', name='warehouse_decision_engine', output='screen'),
    ])
