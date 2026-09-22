# ROS2 Teaching Repository - Ubuntu 22.04 + ROS2 Humble

This repository contains structured materials for teaching ROS2 Humble Hawksbill on Ubuntu 22.04 LTS.

## Environment
- OS: Ubuntu 22.04 LTS
- ROS2 Distribution: Humble Hawksbill  

## Quick Start

### 1. Install ROS2 Humble on Ubuntu 22.04
Follow the official ROS2 installation guide for Ubuntu:
https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debians.html

### 2. Setup Repository
`ash
git clone https://github.com/your-username/ros2-teaching-humble.git
cd ros2-teaching-humble
chmod +x scripts/*.sh
`

### 3. Run Demo
`ash
colcon build
source install/setup.bash
ros2 launch demo_pkg launch_talker_listener.py
`

## Repository Structure

- docs/ - Theoretical explanations
- src/ - Source code examples  
- examples/ - Complete working examples
- exercises/ - Hands-on exercises
- scripts/ - Helper scripts
- tests/ - Test files
- resources/ - Additional resources

## Learning Path

Week 1: ROS2 Fundamentals
Week 2: Topics and Communication
Week 3: Services and Actions
Week 4: Parameters and Launch
Week 5: ROS2 Tools
Week 6+: Advanced Topics

## Following Robotics Back-End

This repository complements Robotics Back-End YouTube tutorials.

## License

MIT License

