"""Message passing for robocluster."""

import asyncio
from collections import defaultdict
from contextlib import suppress
from functools import wraps

from .net import Socket


class Device:
    """A device to interact with the robocluster network."""

    transport = 'json'

    def __init__(self, name, address, loop=None):
        """Initialize the device."""
        self.name = name
        self.events = defaultdict(list)

        self._loop = loop if loop else asyncio.get_event_loop()

        self._sender = Socket(
            address,
            transport=self.transport,
            loop=self._loop
        )
        self._send_queue = asyncio.Queue(loop=self._loop)

        self._receiver = Socket(
            address,
            transport=self.transport,
            loop=self._loop
        )
        self._receiver.bind()

    def publish(self, topic, data):
        """Publish to topic."""
        packet = {
            'event': '{}/{}'.format(self.name, topic),
            'data': data,
        }
        return self._send_queue.put(packet)

    def on(self, event):
        """Add a callback for an event."""
        def _decorator(callback):
            self.events[event].append(callback)
            return callback
        return _decorator

    def task(self, task):
        """Create a background task."""
        self._loop.create_task(task())
        return task

    def every(self, duration):
        """Create a background task that runs every duration."""
        def _decorator(func):
            @wraps(func)
            async def _wrapper():
                while True:
                    await func()
                    await self.sleep(duration)
            self.task(_wrapper)
            return func
        return _decorator

    @staticmethod
    def sleep(seconds):
        """Sleep the device."""
        return asyncio.sleep(seconds)

    async def _send_task(self):
        """Send packets in the send queue."""
        while True:
            packet = await self._send_queue.get()
            await self._sender.send(packet)

    async def _receive_task(self):
        """Recieve packets and call the appropriate callbacks."""
        while True:
            packet, _ = await self._receiver.receive()
            event, data = packet['event'], packet['data']
            for callback in self.events[event]:
                self._loop.create_task(callback(event, data))

    def run_forever(self):
        """Run device in foreground forever."""
        try:
            self._loop.create_task(self._send_task())
            self._loop.create_task(self._receive_task())
            self._loop.run_forever()
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop running device."""
        self._loop.stop()
        for task in asyncio.Task.all_tasks(loop=self._loop):
            task.cancel()
            with suppress(asyncio.CancelledError):
                self._loop.run_until_complete(task)
