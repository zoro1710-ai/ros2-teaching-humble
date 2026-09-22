"""Let the tests run straight from the workspace root, before any build.

Without this, `pytest src/spider_bot/test/` from the workspace root fails with
ModuleNotFoundError unless you have already built and sourced the workspace.
The leg maths in leg_kinematics.py needs neither, and lesson 20 leans on that
being true, so make it true.

colcon test does not need this file - it runs against the installed package.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
