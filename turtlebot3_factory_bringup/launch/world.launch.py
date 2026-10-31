"""Start Gazebo with the factory floor, spawn Burger at the dock, bridge topics."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import AppendEnvironmentVariable, DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    bringup_dir = get_package_share_directory('turtlebot3_factory_bringup')
    tb3_gazebo_dir = get_package_share_directory('turtlebot3_gazebo')

    world = os.path.join(bringup_dir, 'worlds', 'factory_floor.sdf')
    bridge_config = os.path.join(bringup_dir, 'config', 'bridge.yaml')

    use_sim_time = LaunchConfiguration('use_sim_time')
    x_pose = LaunchConfiguration('x_pose')
    y_pose = LaunchConfiguration('y_pose')
    yaw = LaunchConfiguration('yaw')

    declare_args = [
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('x_pose', default_value='0.0',
                              description='Spawn x in metres (dock)'),
        DeclareLaunchArgument('y_pose', default_value='0.0',
                              description='Spawn y in metres (dock)'),
        DeclareLaunchArgument('yaw', default_value='0.0',
                              description='Spawn heading in radians'),
    ]

    set_resource_path = AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH', os.path.join(tb3_gazebo_dir, 'models'))

    ros_gz_sim_dir = get_package_share_directory('ros_gz_sim')
    gz_sim_launch = os.path.join(ros_gz_sim_dir, 'launch', 'gz_sim.launch.py')

    gz_server = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gz_sim_launch),
        launch_arguments={
            'gz_args': ['-r -s -v2 ', world],
            'on_exit_shutdown': 'true',
        }.items())

    gz_gui = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gz_sim_launch),
        launch_arguments={'gz_args': '-g -v2'}.items())

    robot_state_publisher = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(tb3_gazebo_dir, 'launch', 'robot_state_publisher.launch.py')),
        launch_arguments={'use_sim_time': use_sim_time}.items())

    burger_sdf = os.path.join(tb3_gazebo_dir, 'models', 'turtlebot3_burger', 'model.sdf')

    spawn_burger = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-world', 'factory_floor',
            '-name', 'burger',
            '-file', burger_sdf,
            '-x', x_pose,
            '-y', y_pose,
            '-z', '0.01',
            '-Y', yaw,
        ],
        output='screen')

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{
            'config_file': bridge_config,
            'use_sim_time': use_sim_time,
        }],
        output='screen')

    return LaunchDescription(declare_args + [
        set_resource_path,
        SetEnvironmentVariable('TURTLEBOT3_MODEL', 'burger'),
        gz_server,
        gz_gui,
        robot_state_publisher,
        spawn_burger,
        bridge,
    ])
