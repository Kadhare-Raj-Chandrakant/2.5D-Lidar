from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
import os


def generate_launch_description():
    config_file = PathJoinSubstitution([
        FindPackageShare('fovea_lidar'),
        'config',
        'params.yaml'
    ])

    rviz_config = PathJoinSubstitution([
        FindPackageShare('fovea_lidar'),
        'rviz',
        'fovea.rviz'
    ])

    return LaunchDescription([
        DeclareLaunchArgument(
            'config_file',
            default_value=config_file,
            description='Path to config YAML'
        ),
        DeclareLaunchArgument(
            'rviz_config',
            default_value=rviz_config,
            description='Path to RViz config'
        ),
        DeclareLaunchArgument(
            'use_synthetic',
            default_value='true',
            description='Use synthetic data publisher'
        ),
        DeclareLaunchArgument(
            'input_topic',
            default_value='/lidar_points',
            description='Input LiDAR topic'
        ),

        Node(
            package='fovea_lidar',
            executable='fovea_node',
            name='fovea_lidar_node',
            output='screen',
            parameters=[LaunchConfiguration('config_file')],
            arguments=['--ros-args', '--log-level', 'INFO'],
        ),

        TimerAction(
            period=2.0,
            actions=[
                Node(
                    package='fovea_lidar',
                    executable='synthetic_publisher',
                    name='synthetic_publisher',
                    output='screen',
                    condition=lambda context: LaunchConfiguration('use_synthetic').perform(context) == 'true',
                ),
            ],
        ),

        TimerAction(
            period=3.0,
            actions=[
                Node(
                    package='rviz2',
                    executable='rviz2',
                    name='rviz2',
                    output='screen',
                    arguments=['-d', LaunchConfiguration('rviz_config')],
                ),
            ],
        ),
    ])