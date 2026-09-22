import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'turtle_capstone'

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
    description='Capstone project: catch every turtle that appears in turtlesim.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'turtle_spawner = turtle_capstone.turtle_spawner:main',
            'turtle_controller = turtle_capstone.turtle_controller:main',
        ],
    },
)
