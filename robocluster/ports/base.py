from abc import ABC, abstractmethod
from collections import defaultdict

from .loop import Looper
from .message import Message

class Port(ABC, Looper):
    """
    Handles connection over a transport medium

    Reads in bytes from the medium, and emits messages for a router.
    """

    def __init__(self, loop=None):
        super().__init__(loop=loop)
        self._uuid = str(uuid4())
        self._callbacks = defaultdict(list)

        self.add_daemon_task(self._recv_daemon)

    async def _recv_daemon(self):
        while True:
            try:
                msg = await self._recv()
                if msg.type not in self._callbacks:
                    continue
                if msg.source == self._uuid:
                    continue
                self.create_task(self._callbacks[msg.type](msg))
            except BlockingIOError:
                break

    @abstractmethod
    async def _recv(self):
        """Receive a message. Returns message and source."""
        pass

    @abstractmethod
    async def send(self, data):
        """Send a message."""
        pass

    def on_recv(self, type, callback):
        """Add a callback for a message type when received"""
        self._callbacks[type].append(callback)

    def remove_recv_callback(self, type, callback):
        """Removes a callback for a message type"""
        for c in self._callbacks[type]:
            if c == callback:
                self._callbacks[type].remove(c)
