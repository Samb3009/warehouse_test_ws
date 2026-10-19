from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction, SetEnvironmentVariable
from launch.substitutions import PathJoinSubstitution, Command, EnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    description = FindPackageShare("warehouse_description")
    bringup = FindPackageShare("warehouse_bringup")
    environment = FindPackageShare("warehouse_environment")

    xacro_file = PathJoinSubstitution([description, "urdf", "warehouse_robot.urdf.xacro"])
    world_file = PathJoinSubstitution([environment, "worlds", "warehouse.sdf"])
    bridge_file = PathJoinSubstitution([bringup, "config", "gazebo_bridge.yaml"])
    robot_description = ParameterValue(
    Command(["xacro ", xacro_file]),
    value_type=str
)

    # Support both ROS 2 Humble / Gazebo Fortress (IGN_*) and newer Gazebo Sim (GZ_*).
    resource_path = PathJoinSubstitution([environment])
    gz_resource = SetEnvironmentVariable(
        name="GZ_SIM_RESOURCE_PATH",
        value=[resource_path, ":", EnvironmentVariable("GZ_SIM_RESOURCE_PATH", default_value="")]
    )
    ign_resource = SetEnvironmentVariable(
        name="IGN_GAZEBO_RESOURCE_PATH",
        value=[resource_path, ":", EnvironmentVariable("IGN_GAZEBO_RESOURCE_PATH", default_value="")]
    )

    gz_plugin_path = SetEnvironmentVariable(
        name="GZ_SIM_SYSTEM_PLUGIN_PATH",
        value=[
            "/usr/lib/x86_64-linux-gnu/gz-sim-8/plugins",
            ":",
            EnvironmentVariable("GZ_SIM_SYSTEM_PLUGIN_PATH", default_value="")
        ]
    )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare("ros_gz_sim"), "launch", "gz_sim.launch.py"])
        ),
        launch_arguments={"gz_args": [world_file, " -r"]}.items(),
    )

    rsp = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{"robot_description": robot_description, "use_sim_time": True}],
        output="screen",
    )

    # Robot is now defined natively inside warehouse.sdf.
    # Dynamic ros_gz_sim create is intentionally disabled.
    spawn = None

    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=["--ros-args", "-p", ["config_file:=", bridge_file]],
        output="screen",
    )

    battery = Node(
        package="warehouse_battery",
        executable="battery_manager",
        name="battery_manager",
        parameters=[{"use_sim_time": True}],
        output="screen",
    )

    return LaunchDescription([
        DeclareLaunchArgument("rviz", default_value="false"),
        gz_resource, ign_resource, gz_plugin_path, gazebo, rsp,
        TimerAction(period=3.0, actions=[bridge]),
        TimerAction(period=4.0, actions=[battery]),
    ])
