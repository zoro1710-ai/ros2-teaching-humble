"""Where the bridge's bytes go: a real serial port, or a pretend board.

Both classes offer the same three methods, so the bridge does not care which
one it has:

    read_available() -> bytes   whatever has arrived, possibly b''
    write(data)                 send bytes to the board
    close()
"""

import math
import time


class SerialPort:
    """A USB serial connection to a real board."""

    def __init__(self, device, baud):
        # Imported here so 'sim' mode works even without pyserial installed.
        import serial
        # timeout=0: never block, just return what is already there.
        self._serial = serial.Serial(device, baud, timeout=0)

    def read_available(self):
        """Return every byte received so far, or b''."""
        return self._serial.read(self._serial.in_waiting or 1)

    def write(self, data):
        """Send bytes to the board."""
        self._serial.write(data)

    def close(self):
        """Release the port so other programs can use it."""
        self._serial.close()


class SimulatedPort:
    """A pretend board, for trying everything without hardware.

    It behaves like firmware/mcu_bridge with a light sensor and an
    ultrasonic sensor. Driving forward makes the sonar distance shrink, as if
    the robot were rolling towards a wall; at 5 cm the wall "moves" back.
    """

    SAMPLE_PERIOD = 0.1  # seconds, like periodMs = 100 on the board

    def __init__(self):
        self._start = time.monotonic()
        self._last_sample = self._start
        self._pending = b'I simulated board ready\n'
        self._distance = 2.0
        self.left = 0.0
        self.right = 0.0

    def read_available(self):
        """Return any new sample lines, like a board that reports at 10 Hz."""
        now = time.monotonic()
        dt = now - self._last_sample
        if dt >= self.SAMPLE_PERIOD:
            self._last_sample = now
            # Full forward on both wheels = 0.5 m/s towards the wall.
            self._distance -= (self.left + self.right) / 2.0 * 0.5 * dt
            if self._distance < 0.05:
                self._distance = 2.0
            self._distance = min(self._distance, 4.0)

            light = 512 + 400 * math.sin((now - self._start) * 0.5)
            self._pending += b'S range front_sonar %.4f\n' % self._distance
            self._pending += b'S light ldr %.0f\n' % light

        data, self._pending = self._pending, b''
        return data

    def write(self, data):
        """Accept 'M' lines and report when the motor command changes."""
        parts = data.decode('ascii', errors='replace').split()
        if len(parts) != 3 or parts[0] != 'M':
            self._pending += b'E unknown command\n'
            return
        command = (float(parts[1]), float(parts[2]))
        if command != (self.left, self.right):
            self.left, self.right = command
            self._pending += b'I motors %.2f %.2f\n' % command

    def close(self):
        """Nothing to release."""


def open_port(device, baud):
    """Open a serial port, or the pretend board when device is 'sim'."""
    if device == 'sim':
        return SimulatedPort()
    return SerialPort(device, baud)
