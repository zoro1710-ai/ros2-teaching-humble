# 00 — Install and set up

**Goal:** a working ROS 2 Humble installation and this repository built.

Humble Hawksbill is the LTS release that pairs with **Ubuntu 22.04**. Other
Ubuntu versions are not supported by the binary packages; if you are on 24.04
use Jazzy instead, or use the Docker image in this repo.

---

## 1. Install ROS 2 Humble

```bash
# Locale must be UTF-8
sudo apt update && sudo apt install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# Enable the Ubuntu Universe repository
sudo apt install -y software-properties-common
sudo add-apt-repository universe

# Add the ROS 2 apt key and repository
sudo apt update && sudo apt install -y curl
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
    | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# Install the desktop variant (includes RViz, turtlesim, demo nodes)
sudo apt update
sudo apt install -y ros-humble-desktop

# Build tools used by this course
sudo apt install -y python3-colcon-common-extensions python3-rosdep python3-pytest
sudo rosdep init      # harmless "already exists" error if you ran it before
rosdep update
```

The official page is
<https://docs.ros.org/en/humble/Installation/Alternatives/Ubuntu-Development-Setup.html> — if
a command above ever fails, that page is the source of truth.

### Not on Ubuntu 22.04?

Use the container that ships with this repo:

```bash
docker build -t ros2-basics -f docker/Dockerfile .
./docker/run.sh
```

It mounts the repository at `~/ros2_ws` inside the container and forwards the
display, so `turtlesim` and `rviz2` work. VS Code users can instead
"Reopen in Container" — `.devcontainer/` is already configured.

---

## 2. Source ROS 2

Nothing works until your shell knows where ROS 2 is:

```bash
source /opt/ros/humble/setup.bash
```

This is per-terminal. Add it to your shell startup so you never think about it
again:

```bash
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
```

Check it took effect:

```bash
echo $ROS_DISTRO     # -> humble
ros2 --help
```

---

## 3. Get and build this repository

```bash
git clone https://github.com/zoro1710-ai/ros2-teaching-humble.git
cd ros2-teaching-humble

# Install any system dependencies the packages declare
rosdep install --from-paths src --ignore-src -y --rosdistro humble

# Build
colcon build --symlink-install

# Make the freshly built packages visible to ros2
source install/setup.bash
```

Or just use the helper: `./scripts/build.sh`.

### Check everything

```bash
python3 scripts/verify_setup.py
```
If python is not installed then:
```bash
sudo apt update
sudo apt install -y python3 python3-pip
```

It checks each thing that commonly breaks and prints the exact fix.

---

## 4. Your first run

```bash
ros2 launch ros2_basics_py talker_listener.launch.py
```

You should see a talker publishing and a listener receiving. Press `Ctrl+C`
to stop both.

---

## The three traps everyone hits

**1. "Package not found" right after building.**
You did not source the workspace. Every new terminal needs:

```bash
source /opt/ros/humble/setup.bash     # the ROS installation
source install/setup.bash             # this workspace, from the repo root
```

Order matters: the underlay (`/opt/ros`) first, then your overlay.

**2. Sourcing `install/setup.bash` from the wrong directory.**
It is a relative path. Run it from the workspace root, or use the absolute
path.

**3. Building while the workspace is sourced in that same terminal.**
It works, but it can produce confusing stale results. The clean habit: one
terminal for building, others for running.

---

## What you should be able to do now

- [ ] `echo $ROS_DISTRO` prints `humble`
- [ ] `colcon build` finishes without errors
- [ ] `ros2 pkg list | grep ros2_basics` shows the course packages
- [ ] `python3 scripts/verify_setup.py` reports everything ok

**Next:** [01 — ROS 2 fundamentals](01-ros2-fundamentals.md)
