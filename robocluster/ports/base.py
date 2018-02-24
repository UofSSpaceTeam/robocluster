from abc import ABC, abstractmethod
from collections import defaultdict
from uuid import uuid4

from ..loop import Looper
from ..message import Message


BUFFER_SIZE = 1024

class Port(ABC, Looper):
    """
    Handles connection over a transport medium

    Reads in bytes from the medium, and emits messages for a router.
    """

    def __init__(self, codec='json', loop=None):
        super().__init__(loop=loop)

        self._uuid = str(uuid4())

        self.codec = codec
        self._callbacks = defaultdict(set)

        self.add_daemon_task(self._recv_daemon)

    async def _recv_daemon(self):
        while True:
            # TODO: we need to do some good error checking here...
            msg, source = await self._recv()
            if msg is None:
                continue
            if msg.type not in self._callbacks:
                continue
            if msg.source == self._uuid:
                continue
            for cb in self._callbacks[msg.type]:
                self.create_task(cb(source, msg))

    @abstractmethod
    async def _recv(self):
        """Receive a Message from the port."""
        pass

    @abstractmethod
    async def send(self, msg):
        """Send a Message."""
        pass

    def on_recv(self, type, callback):
        """Add a callback for a message type when received"""
        self._callbacks[type].add(callback)

    def remove_recv_callback(self, type, callback):
        """
        Removes a callback for a message type.

        Note: This operation is idempotent.
        """
        if type in self._callbacks:
            self._callbacks[type].discard(callback)
            if not self._callbacks[type]:
                # remove the type if there are no callbacks if empty
                del self._callbacks[type]
