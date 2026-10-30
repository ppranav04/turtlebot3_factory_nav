"""Station simulator and FIFO pickup dispatcher. Start after factory_sim."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    bringup_dir = get_package_share_directory('turtlebot3_factory_bringup')
    stations_file = os.path.join(bringup_dir, 'config', 'stations.yaml')
    params = [{'use_sim_time': True, 'stations_file': stations_file}]

    station_sim = Node(
        package='turtlebot3_factory_nav',
        executable='station_sim',
        parameters=params,
        output='screen')

    task_dispatcher = Node(
        package='turtlebot3_factory_nav',
        executable='task_dispatcher',
        parameters=params,
        output='screen')

    return LaunchDescription([
        station_sim,
        task_dispatcher,
    ])
