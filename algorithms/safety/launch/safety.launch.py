import os
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    params_file = os.path.join(
        get_package_share_directory('safety'),
        'config',
        'params.yaml',
    )

    safety_brake_node = Node(
        package='safety',
        executable='safety_brake_node',
        name='safety_brake_node',
        parameters=[params_file],
        output='screen',
    )

    return LaunchDescription([safety_brake_node])
