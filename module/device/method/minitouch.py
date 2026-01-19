"""
MiniTouch
"""

import json
import numpy as np

from module.base.utils import random_rectangle_point
from module.exception import ScriptError
from module.logger import logger


def random_normal_distribution(a, b, n=5):
    output = np.mean(np.random.uniform(a, b, size=n))
    return output


def random_theta():
    theta = np.random.uniform(0, 2 * np.pi)
    return np.array([np.sin(theta), np.cos(theta)])


def random_rho(dis):
    return random_normal_distribution(-dis, dis)


def insert_swipe(p0, p3, speed=15, min_distance=10):
    """
    Insert way point from start to end.
    First generate a cubic bézier curve

    Args:
        p0: Start point.
        p3: End point.
        speed: Average move speed, pixels per 10ms.
        min_distance:

    Returns:
        list[list[int]]: List of points.

    Examples:
        > insert_swipe((400, 400), (600, 600), speed=20)
        [[400, 400], [406, 406], [416, 415], [429, 428], [444, 442], [462, 459], [481, 478], [504, 500], [527, 522],
        [545, 540], [560, 557], [573, 570], [584, 582], [592, 590], [597, 596], [600, 600]]
    """
    p0 = np.array(p0)
    p3 = np.array(p3)

    # Random control points in Bézier curve
    distance = np.linalg.norm(p3 - p0)
    p1 = 2 / 3 * p0 + 1 / 3 * p3 + random_theta() * random_rho(distance * 0.1)
    p2 = 1 / 3 * p0 + 2 / 3 * p3 + random_theta() * random_rho(distance * 0.1)

    # Random `t` on Bézier curve, sparse in the middle, dense at start and end
    segments = max(int(distance / speed) + 1, 5)
    lower = random_normal_distribution(-85, -60)
    upper = random_normal_distribution(80, 90)
    theta = np.arange(lower + 0.0, upper + 0.0001, (upper - lower) / segments)
    ts = np.sin(theta / 180 * np.pi)
    ts = np.sign(ts) * abs(ts) ** 0.9
    ts = (ts - min(ts)) / (max(ts) - min(ts))

    # Generate cubic Bézier curve
    points = []
    prev = (-100, -100)
    for t in ts:
        point = (
            p0 * (1 - t) ** 3
            + 3 * p1 * t * (1 - t) ** 2
            + 3 * p2 * t**2 * (1 - t)
            + p3 * t**3
        )
        point = point.astype(int).tolist()
        if np.linalg.norm(np.subtract(point, prev)) < min_distance:
            continue

        points.append(point)
        prev = point

    # Delete nearing points
    if len(points[1:]):
        distance = np.linalg.norm(np.subtract(points[1:], points[0]), axis=1)
        mask = np.append(True, distance > min_distance)
        points = np.array(points)[mask].tolist()
        if len(points) <= 1:
            points = [p0, p3]
    else:
        points = [p0, p3]

    return points


class Command:
    def __init__(
        self,
        operation: str,
        contact: int = 0,
        x: int = 0,
        y: int = 0,
        ms: int = 10,
        pressure: int = 100,
        mode: int = 0,
        text: str = "",
    ):
        """
        See https://github.com/openstf/minitouch#writable-to-the-socket

        Args:
            operation: c, r, d, m, u, w
            contact:
            x:
            y:
            ms:
            pressure:
            mode:
            text:
        """
        self.operation = operation
        self.contact = contact
        self.x = x
        self.y = y
        self.ms = ms
        self.pressure = pressure
        self.mode = mode
        self.text = text

    def to_minitouch(self) -> str:
        """
        String that write into minitouch socket
        """
        if self.operation == "c":
            return f"{self.operation}\n"
        elif self.operation == "r":
            return f"{self.operation}\n"
        elif self.operation == "d":
            return (
                f"{self.operation} {self.contact} {self.x} {self.y} {self.pressure}\n"
            )
        elif self.operation == "m":
            return (
                f"{self.operation} {self.contact} {self.x} {self.y} {self.pressure}\n"
            )
        elif self.operation == "u":
            return f"{self.operation} {self.contact}\n"
        elif self.operation == "w":
            return f"{self.operation} {self.ms}\n"
        else:
            return ""

    def to_maatouch_sync(self):
        if self.operation == "c":
            return f"{self.operation}\n"
        elif self.operation == "r":
            if self.mode:
                return f"{self.operation} {self.mode}\n"
            else:
                return f"{self.operation}\n"
        elif self.operation == "d":
            if self.mode:
                return f"{self.operation} {self.contact} {self.x} {self.y} {self.pressure} {self.mode}\n"
            else:
                return f"{self.operation} {self.contact} {self.x} {self.y} {self.pressure}\n"
        elif self.operation == "m":
            if self.mode:
                return f"{self.operation} {self.contact} {self.x} {self.y} {self.pressure} {self.mode}\n"
            else:
                return f"{self.operation} {self.contact} {self.x} {self.y} {self.pressure}\n"
        elif self.operation == "u":
            if self.mode:
                return f"{self.operation} {self.contact} {self.mode}\n"
            else:
                return f"{self.operation} {self.ms}\n"
        elif self.operation == "w":
            return f"{self.operation} {self.ms}\n"
        elif self.operation == "s":
            return f"{self.operation} {self.text}\n"
        else:
            return ""


class CommandBuilder:
    """Build command str for minitouch.

    You can use this, to custom actions as you wish::

        with safe_connection(_DEVICE_ID) as connection:
            builder = CommandBuilder()
            builder.down(0, 400, 400, 50)
            builder.commit()
            builder.move(0, 500, 500, 50)
            builder.commit()
            builder.move(0, 800, 400, 50)
            builder.commit()
            builder.up(0)
            builder.commit()
            builder.publish(connection)

    """

    DEFAULT_DELAY = 0.05
    max_x = 1280
    max_y = 720

    def __init__(
        self,
        device,
        contact=0,
        handle_orientation=True,
    ):
        """
        Args:
            device:
        """
        self.device = device
        self.commands = []
        self.delay = 0
        self.contact = contact
        self.handle_orientation = handle_orientation

    @property
    def orientation(self):
        if self.handle_orientation:
            return self.device.orientation
        else:
            return 0

    def convert(self, x, y):
        max_x, max_y = self.device.max_x, self.device.max_y
        orientation = self.orientation

        if orientation == 0:
            pass
        elif orientation == 1:
            x, y = 720 - y, x
            max_x, max_y = max_y, max_x
        elif orientation == 2:
            x, y = 1280 - x, 720 - y
        elif orientation == 3:
            x, y = y, 1280 - x
            max_x, max_y = max_y, max_x
        else:
            raise ScriptError(f"Invalid device orientation: {orientation}")

        self.max_x, self.max_y = max_x, max_y
        # Maximum X and Y coordinates may, but usually do not, match the display size.
        x, y = int(x / 1280 * max_x), int(y / 720 * max_y)
        return x, y

    def commit(self):
        """add minitouch command: 'c\n'"""
        self.commands.append(Command("c"))
        return self

    def reset(self, mode=0):
        """add minitouch command: 'r\n'"""
        self.commands.append(Command("r", mode=mode))
        return self

    def wait(self, ms=10):
        """add minitouch command: 'w <ms>\n'"""
        self.commands.append(Command("w", ms=ms))
        self.delay += ms
        return self

    def up(self, mode=0):
        """add minitouch command: 'u <contact>\n'"""
        self.commands.append(Command("u", contact=self.contact, mode=mode))
        return self

    def down(self, x, y, pressure=100, mode=0):
        """add minitouch command: 'd <contact> <x> <y> <pressure>\n'"""
        x, y = self.convert(x, y)
        self.commands.append(
            Command("d", x=x, y=y, contact=self.contact, pressure=pressure, mode=mode)
        )
        return self

    def move(self, x, y, pressure=100, mode=0):
        """add minitouch command: 'm <contact> <x> <y> <pressure>\n'"""
        x, y = self.convert(x, y)
        self.commands.append(
            Command("m", x=x, y=y, contact=self.contact, pressure=pressure, mode=mode)
        )
        return self

    def clear(self):
        """clear current commands"""
        self.commands = []
        self.delay = 0
        return self

    def to_minitouch(self) -> str:
        out = "".join([command.to_minitouch() for command in self.commands])
        self._check_empty(out)
        return out

    def to_maatouch_sync(self) -> str:
        out = "".join([command.to_maatouch_sync() for command in self.commands])
        self._check_empty(out)
        return out

    def send(self):
        return self.device.maatouch_send(builder=self)

    def _check_empty(self, text=None):
        """
        A valid command list must includes some operations not just committing

        Returns:
            bool: If command is empty
        """
        empty = True
        for command in self.commands:
            if command.operation not in ["c", "w", "s"]:
                empty = False
                break
        if empty:
            logger.warning(
                f"Command list empty, sending it may cause unexpected behaviour: {text}"
            )
        return empty
