"""Factory floor world, Burger, Nav2 (AMCL + map server) and RViz."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    bringup_dir = get_package_share_directory('turtlebot3_factory_bringup')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    map_yaml = os.path.join(bringup_dir, 'maps', 'factory_floor.yaml')
    nav2_params = os.path.join(bringup_dir, 'config', 'nav2_params.yaml')

    rviz_config = os.path.join(bringup_dir, 'rviz', 'factory.rviz')

    cart_sdf = os.path.join(bringup_dir, 'worlds', 'cart.sdf')
    cart_x = 0.8

    world = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_dir, 'launch', 'world.launch.py')))

    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')),
        launch_arguments={
            'map': map_yaml,
            'params_file': nav2_params,
            'use_sim_time': 'true',
        }.items())

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}],
        output='screen')

    spawn_cart = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-world', 'factory_floor', '-name', 'cart',
                   '-file', cart_sdf, '-x', str(cart_x), '-y', '1.1', '-z', '0.0'],
        output='screen')

    cart_patrol = Node(
        package='turtlebot3_factory_nav',
        executable='cart_patrol',
        parameters=[{'use_sim_time': True, 'x': cart_x}],
        output='screen'
    )

    return LaunchDescription([
        world,
        nav2,
        rviz,
        spawn_cart,
        cart_patrol,
    ])
