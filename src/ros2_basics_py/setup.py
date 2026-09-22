import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'ros2_basics_py'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        # Tells the ament index that this package exists.
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Anything you want to `ros2 launch` must be installed into share/.
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.xml')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Aaditya',
    maintainer_email='daaditya550@gmail.com',
    description='Runnable rclpy examples for every lesson of the ROS 2 basics course.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # 03 - nodes
            'minimal_node = ros2_basics_py.minimal_node:main',
            'timer_node = ros2_basics_py.timer_node:main',
            # 04 - topics
            'talker = ros2_basics_py.talker:main',
            'listener = ros2_basics_py.listener:main',
            'number_publisher = ros2_basics_py.number_publisher:main',
            'number_counter = ros2_basics_py.number_counter:main',
            # 05 - services
            'add_two_ints_server = ros2_basics_py.add_two_ints_server:main',
            'add_two_ints_client = ros2_basics_py.add_two_ints_client:main',
            'led_panel = ros2_basics_py.led_panel:main',
            'battery_node = ros2_basics_py.battery_node:main',
            # 06 - custom interfaces
            'hardware_status_publisher = ros2_basics_py.hardware_status_publisher:main',
            'sensor_reading_publisher = ros2_basics_py.sensor_reading_publisher:main',
            'rectangle_area_server = ros2_basics_py.rectangle_area_server:main',
            'rectangle_area_client = ros2_basics_py.rectangle_area_client:main',
            # 07 - parameters
            'parameter_demo = ros2_basics_py.parameter_demo:main',
            # 09 - actions
            'count_until_server = ros2_basics_py.count_until_server:main',
            'count_until_client = ros2_basics_py.count_until_client:main',
            # 10 - QoS
            'qos_publisher = ros2_basics_py.qos_publisher:main',
            'qos_subscriber = ros2_basics_py.qos_subscriber:main',
            # 11 - executors
            'executor_demo = ros2_basics_py.executor_demo:main',
            # 12 - TF2
            'static_tf_broadcaster = ros2_basics_py.static_tf_broadcaster:main',
            'tf_broadcaster = ros2_basics_py.tf_broadcaster:main',
            'tf_listener = ros2_basics_py.tf_listener:main',
            # 13 - lifecycle
            'lifecycle_number_publisher = ros2_basics_py.lifecycle_number_publisher:main',
        ],
    },
)
