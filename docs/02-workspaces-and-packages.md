# 02 — Workspaces and packages

**Goal:** know what colcon builds, why sourcing matters, and how to create
your own package.

---

## The workspace

A workspace is just a directory with a `src/` folder in it. After a build it
looks like this:

```
ros2-teaching-humble/          <- workspace root (run colcon from here)
├── src/                       <- YOUR code. The only directory you edit.
│   ├── ros2_basics_interfaces/
│   ├── ros2_basics_py/
│   └── turtle_capstone/
├── build/                     <- intermediate build files   (git-ignored)
├── install/                   <- what you actually run       (git-ignored)
└── log/                       <- build and test logs         (git-ignored)
```

`build/`, `install/` and `log/` are generated. Never commit them, never edit
them. If a build goes strange, delete all three (`./scripts/clean.sh`) and
build again — that fixes a surprising number of problems.

## Underlay and overlay

```
/opt/ros/humble/     the underlay  - the ROS 2 installation
<workspace>/install/ the overlay   - your packages, layered on top
```

Source the underlay first, then the overlay:

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
```

The overlay shadows the underlay: if you build a package with the same name as
one in `/opt/ros`, yours wins. That is how you patch a system package locally.

---

## Building with colcon

```bash
colcon build --symlink-install
```

| Flag | What it does |
|---|---|
| `--symlink-install` | installs symlinks to your Python files instead of copies, so edits take effect without rebuilding |
| `--packages-select X` | build only X |
| `--packages-up-to X` | build X and everything it depends on |
| `--event-handlers console_direct+` | show compiler/test output live instead of hiding it |
| `--continue-on-error` | keep building the other packages after one fails |

**Even with `--symlink-install` you must rebuild after:**

- adding or renaming an entry point in `setup.py`
- adding a launch file, config file, or anything in `data_files`
- any change inside `ros2_basics_interfaces` (messages are generated code)
- adding a new package

Then `source install/setup.bash` again, in every terminal.

---

## What a package is

A package is the unit ROS 2 builds, installs and depends on. The minimum is a
directory in `src/` containing a `package.xml`.

### Two build types

| | `ament_python` | `ament_cmake` |
|---|---|---|
| Language | Python | C++ (and interface generation) |
| Marker files | `setup.py`, `setup.cfg`, `resource/<pkg>` | `CMakeLists.txt` |
| Used here by | `ros2_basics_py`, `turtle_capstone` | `ros2_basics_interfaces` |

**Custom messages always need `ament_cmake`,** even when only Python nodes use
them. That is why this repo keeps its interfaces in a separate package — the
standard layout, and it stops your Python package from needing CMake.

### Anatomy of the Python package in this repo

```
src/ros2_basics_py/
├── package.xml                 <- name, version, dependencies
├── setup.py                    <- what to install, and the entry points
├── setup.cfg                   <- tells setuptools where scripts go
├── resource/ros2_basics_py     <- empty marker file; registers the package
├── ros2_basics_py/             <- the actual Python module
│   ├── __init__.py
│   ├── talker.py
│   └── ...
├── launch/
├── config/
└── test/
```

Two files do the real work.

**`package.xml`** declares dependencies. `rosdep` reads it to install system
packages, and colcon reads it to work out build order.

```xml
<depend>rclpy</depend>                     <!-- needed to build AND run -->
<exec_depend>ros2launch</exec_depend>      <!-- only needed at runtime -->
<test_depend>python3-pytest</test_depend>  <!-- only needed for tests -->
```

**`setup.py`** maps a command name to a Python function:

```python
entry_points={
    'console_scripts': [
        'talker = ros2_basics_py.talker:main',
    ],
},
```

That single line is what makes `ros2 run ros2_basics_py talker` work. The left
side is the executable name, the right side is `module:function`.

Anything you want to `ros2 launch` must also be listed in `data_files`, or it
will not be installed into `share/` and launch will not find it.

---

## Create your own package

```bash
cd src

# Python
ros2 pkg create --build-type ament_python --license MIT my_package \
    --dependencies rclpy std_msgs

# C++ (for reference)
ros2 pkg create --build-type ament_cmake --license MIT my_cpp_package \
    --dependencies rclcpp std_msgs
```

Then:

```bash
cd ..
colcon build --packages-select my_package
source install/setup.bash
```

---

## Common mistakes

**`Package 'my_package' not found`**
Either the build failed, or you did not `source install/setup.bash` in this
terminal. Check `ros2 pkg list | grep my_package`.

**`No executable found`**
The package built, but the entry point is missing or misspelled in
`setup.py` — or you added it and did not rebuild.

**Edited a Python file, nothing changed**
You built without `--symlink-install`. Rebuild with it.

**`file 'launch/x.launch.py' was not found`**
The launch file is not in `data_files` in `setup.py`, so it was never
installed. Check `install/my_package/share/my_package/launch/`.

**colcon builds packages in the wrong order**
It uses `package.xml` to order the build. If package A uses package B's
messages, A must declare `<depend>B</depend>`.

---

## Check yourself

- [ ] Why can't a pure `ament_python` package define custom messages?
- [ ] You added `talker2` to `setup.py`. What must you do before
      `ros2 run` finds it?
- [ ] What is the difference between `<depend>` and `<exec_depend>`?
- [ ] What does `--symlink-install` actually change?

**Next:** [03 — Nodes](03-nodes.md)
