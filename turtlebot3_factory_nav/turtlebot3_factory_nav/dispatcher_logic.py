"""FIFO pickup dispatcher state machine. Pure Python, no ROS imports."""
from collections import deque
from dataclasses import dataclass
from enum import Enum

NAVIGATE = 'navigate'
WAIT = 'wait'
REMOVE_BOX = 'remove_box'
SPAWN_BOX = 'spawn_box'
STATION_DONE = 'station_done'

STORAGE = 'storage'
DOCK = 'dock'


class State(Enum):
    """Where the robot is in a pickup cycle."""

    IDLE = 'IDLE'
    TO_STATION = 'TO_STATION'
    AT_STATION = 'AT_STATION'
    TO_STORAGE = 'TO_STORAGE'
    TO_DOCK = 'TO_DOCK'


@dataclass(frozen=True)
class Action:
    """One command for the ROS node to carry out."""

    kind: str
    arg: object = None


class Dispatcher:
    """FIFO queue of station pickups and the robot's cycle through them."""

    def __init__(self, dwell_s=3.0, max_queue=4):
        self.dwell_s = dwell_s
        self.max_queue = max_queue
        self._state = State.IDLE
        self._current = None
        self._queue = deque()

    @property
    def state(self):
        """Return the current State."""
        return self._state

    @property
    def current(self):
        """Return the station being served, or None."""
        return self._current

    @property
    def queue(self):
        """Return a copy of the waiting station ids, oldest first."""
        return list(self._queue)

    def _next_job(self):
        """Start the oldest queued pickup, or head to the dock if none."""
        if self._queue:
            self._current = self._queue.popleft()
            self._state = State.TO_STATION
            return [Action(NAVIGATE, self._current)]
        self._current = None
        self._state = State.TO_DOCK
        return [Action(NAVIGATE, DOCK)]

    def on_request(self, station_id):
        """Queue a pickup request; start it at once if the robot is free."""
        if station_id == self._current or station_id in self._queue:
            return []
        if len(self._queue) >= self.max_queue:
            return []
        self._queue.append(station_id)
        if self._state in (State.IDLE, State.TO_DOCK):
            return self._next_job()
        return []

    def on_nav_succeeded(self):
        """Advance the cycle when the robot reaches its goal."""
        if self._state == State.TO_STATION:
            self._state = State.AT_STATION
            return [Action(WAIT, self.dwell_s)]
        if self._state == State.TO_STORAGE:
            done = self._current
            return [Action(SPAWN_BOX, done), Action(STATION_DONE, done)] + self._next_job()
        if self._state == State.TO_DOCK:
            self._state = State.IDLE
            return []
        return []

    def on_nav_failed(self):
        """Handle a failed navigation goal."""
        if self._state == State.TO_STATION:
            self._queue.append(self._current)
            return self._next_job()
        if self._state == State.TO_STORAGE:
            return [Action(NAVIGATE, STORAGE)]
        if self._state == State.TO_DOCK:
            return [Action(NAVIGATE, DOCK)]
        return []

    def on_dwell_done(self):
        """Finish the simulated pickup and head to storage."""
        if self._state != State.AT_STATION:
            return []
        self._state = State.TO_STORAGE
        return [Action(REMOVE_BOX, self._current), Action(NAVIGATE, STORAGE)]
