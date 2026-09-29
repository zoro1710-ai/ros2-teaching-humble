import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'mcu_bridge'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Aaditya',
    maintainer_email='daaditya550@gmail.com',
    description='Boilerplate: any microcontroller sensor to a ROS topic, and /cmd_vel to motors.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'mcu_bridge = mcu_bridge.bridge_node:main',
            'keyboard_teleop = mcu_bridge.keyboard_teleop:main',
        ],
    },
)
