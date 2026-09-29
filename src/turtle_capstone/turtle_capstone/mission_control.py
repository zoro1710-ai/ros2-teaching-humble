#!/usr/bin/env python3
"""Grand finale - every concept in one node, driven by a single action goal.

This is the "combined crazy show". You send ONE action goal ("catch 5 turtles")
and this node runs an autonomous hunt that you can watch and cancel live. On the
way it exercises all five concepts of the course at once:

    NODES       this node + turtlesim, talking over the graph
    TOPICS      subscribes /turtle1/pose      (where am I)
                publishes  /turtle1/cmd_vel   (how I move)
                publishes  /alive_turtles     (the current world state, for rqt)
    SERVICES    calls /spawn and /kill on turtlesim (make / remove a turtle)
    PARAMETERS  linear_gain, angular_gain, catch_distance, update_rate - and they
                are re-read every tick, so `ros2 param set` retunes it mid-hunt
    ACTIONS     the whole mission IS an action: goal in, feedback streaming out,
                a real result at the end, and cancel that stops the turtle cleanly

The trick that makes an action server able to run a control loop AND still
service its pose subscription and its /spawn /kill futures is a
ReentrantCallbackGroup on a MultiThreadedExecutor (see main). That is lesson 11
doing real work.
"""

import math
import random
import time

from geometry_msgs.msg import Twist
import rclpy
from rclpy.action import ActionServer, CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from ros2_basics_interfaces.action import CatchMission
from ros2_basics_interfaces.msg import Turtle, TurtleArray
from turtlesim.msg import Pose
from turtlesim.srv import Kill, Spawn


def normalize_angle(angle):
    """Wrap an angle in radians into the range [-pi, pi]."""
    while angle > math.pi:
        angle -= 2.0 * math.pi
    while angle < -math.pi:
        angle += 2.0 * math.pi
    return angle


class MissionControl(Node):
    """One action server that spawns, hunts and catches turtles on demand."""

    def __init__(self):
        super().__init__('mission_control')

        # PARAMETERS - everything tunable, and re-read every tick so that
        # `ros2 param set /mission_control linear_gain 4.0` changes the running
        # hunt without a restart.
        self.declare_parameter('linear_gain', 2.0)
        self.declare_parameter('angular_gain', 6.0)
        self.declare_parameter('catch_distance', 0.5)
        self.declare_parameter('update_rate', 50.0)
        self.declare_parameter('spawn_x_range', [1.0, 10.0])
        self.declare_parameter('spawn_y_range', [1.0, 10.0])

        # A reentrant group lets the pose subscription, the service futures and
        # the long-running action callback all make progress at the same time.
        self._cb_group = ReentrantCallbackGroup()

        self._pose = None
        # Counts up for the life of the node so names never collide, even when
        # you run several missions without restarting turtlesim.
        self._spawn_counter = 0

        # TOPICS
        self._cmd_publisher = self.create_publisher(Twist, 'turtle1/cmd_vel', 10)
        self._alive_publisher = self.create_publisher(TurtleArray, 'alive_turtles', 10)
        self._pose_subscriber = self.create_subscription(
            Pose, 'turtle1/pose', self._on_pose, 10, callback_group=self._cb_group)

        # SERVICES (clients on turtlesim's own services)
        self._spawn_client = self.create_client(
            Spawn, 'spawn', callback_group=self._cb_group)
        self._kill_client = self.create_client(
            Kill, 'kill', callback_group=self._cb_group)

        # ACTION
        self._action_server = ActionServer(
            self,
            CatchMission,
            'catch_mission',
            execute_callback=self._execute_mission,
            cancel_callback=self._on_cancel,
            callback_group=self._cb_group)

        self.get_logger().info('mission_control ready - send a catch_mission goal')

    # --- topic input ---
    def _on_pose(self, msg):
        self._pose = msg

    # --- action plumbing ---
    def _on_cancel(self, goal_handle):
        self.get_logger().info('cancel requested - the turtle will stop')
        return CancelResponse.ACCEPT

    def _execute_mission(self, goal_handle):
        count = max(0, goal_handle.request.turtle_count)
        self.get_logger().info('mission started: catch %d turtles' % count)

        if not self._wait_for_services():
            goal_handle.abort()
            return CatchMission.Result()

        targets = self._spawn_turtles(count)
        start = time.time()
        caught = 0
        rate_hz = float(self.get_parameter('update_rate').value)
        period = 1.0 / rate_hz if rate_hz > 0 else 0.02

        while targets:
            # Cancel: stop the turtle where it is and hand back what we managed.
            if goal_handle.is_cancel_requested:
                self._stop()
                goal_handle.canceled()
                self.get_logger().info('mission canceled after %d catches' % caught)
                return self._result(caught, start)

            # No pose has arrived yet: keep still and wait one tick.
            if self._pose is None:
                self._stop()
                time.sleep(period)
                continue

            # Live parameters - retunable from the terminal mid-hunt.
            linear_gain = float(self.get_parameter('linear_gain').value)
            angular_gain = float(self.get_parameter('angular_gain').value)
            catch_distance = float(self.get_parameter('catch_distance').value)

            target = min(targets, key=self._distance_to)
            distance = self._distance_to(target)

            if distance > catch_distance:
                cmd = Twist()
                heading = math.atan2(target['y'] - self._pose.y,
                                     target['x'] - self._pose.x)
                heading_error = normalize_angle(heading - self._pose.theta)
                cmd.linear.x = linear_gain * distance
                cmd.angular.z = angular_gain * heading_error
                self._cmd_publisher.publish(cmd)
            else:
                # Close enough: SERVICE call to remove it, then count it.
                self._kill(target['name'])
                targets.remove(target)
                caught += 1
                self._stop()

            self._publish_alive(targets)
            self._publish_feedback(goal_handle, caught, targets, target, distance)
            time.sleep(period)

        self._stop()
        self._publish_alive(targets)
        goal_handle.succeed()
        self.get_logger().info('mission complete: %d caught' % caught)
        return self._result(caught, start)

    # --- helpers ---
    def _wait_for_services(self, timeout=5.0):
        deadline = time.time() + timeout
        for client, name in ((self._spawn_client, '/spawn'),
                             (self._kill_client, '/kill')):
            while not client.service_is_ready():
                if time.time() > deadline:
                    self.get_logger().error('%s never showed up' % name)
                    return False
                time.sleep(0.1)
        return True

    def _spawn_turtles(self, count):
        x_range = self.get_parameter('spawn_x_range').value
        y_range = self.get_parameter('spawn_y_range').value
        targets = []
        for _ in range(count):
            self._spawn_counter += 1
            request = Spawn.Request()
            request.x = random.uniform(x_range[0], x_range[1])
            request.y = random.uniform(y_range[0], y_range[1])
            request.theta = random.uniform(0.0, 2.0 * math.pi)
            request.name = 'prey%d' % self._spawn_counter
            result = self._call(self._spawn_client, request)
            # turtlesim echoes the name it used; it is empty only if the spawn
            # was refused, in which case fall back to the name we asked for.
            name = result.name if result and result.name else request.name
            targets.append({'name': name, 'x': request.x, 'y': request.y})
        self.get_logger().info('spawned %d turtles' % len(targets))
        return targets

    def _kill(self, name):
        request = Kill.Request()
        request.name = name
        self._call(self._kill_client, request)

    def _call(self, client, request):
        """Call a service and block this thread until it answers.

        Safe only because we run on a MultiThreadedExecutor: another thread
        completes the future while this one waits.
        """
        future = client.call_async(request)
        while not future.done():
            time.sleep(0.005)
        return future.result()

    def _distance_to(self, target):
        return math.hypot(target['x'] - self._pose.x, target['y'] - self._pose.y)

    def _stop(self):
        self._cmd_publisher.publish(Twist())

    def _publish_alive(self, targets):
        msg = TurtleArray()
        msg.turtles = [Turtle(name=t['name'], x=t['x'], y=t['y'], theta=0.0)
                       for t in targets]
        self._alive_publisher.publish(msg)

    def _publish_feedback(self, goal_handle, caught, targets, target, distance):
        fb = CatchMission.Feedback()
        fb.caught_so_far = caught
        fb.remaining = len(targets)
        fb.current_target = target['name'] if targets else ''
        fb.distance_to_target = distance if targets else 0.0
        goal_handle.publish_feedback(fb)

    def _result(self, caught, start):
        result = CatchMission.Result()
        result.total_caught = caught
        result.elapsed_seconds = time.time() - start
        return result


def main(args=None):
    rclpy.init(args=args)
    node = MissionControl()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
