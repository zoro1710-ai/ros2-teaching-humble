import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'spider_bot'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Anything ros2 launch, xacro or RViz must find has to be installed.
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*.xacro')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'config'), glob('config/*.rviz')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Aaditya',
    maintainer_email='daaditya550@gmail.com',
    description='A four legged robot: description, leg IK, gait and cmd_vel bridge.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # 21 - the gait, publishing /joint_states straight to RViz
            'gait_controller = spider_bot.gait_controller:main',
            # 19 - the same gait, sending commands to ros2_control
            'gait_to_controller = spider_bot.gait_to_controller:main',
        ],
    },
)
