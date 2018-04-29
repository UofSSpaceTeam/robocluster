"""Message passing for robocluster."""

import asyncio
import hashlib
import threading
from collections import defaultdict
from contextlib import suppress
from fnmatch import fnmatch
from functools import wraps

from .looper import Looper
from .member import Member
from .util import duration_to_seconds, as_coroutine

class AttributeDict(dict):
    """
    A dictionary that allows you to acces entries like
    you would attributes in an object.
    """
    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        del self[name]


def group_to_port(group):
    h = hashlib.sha256(group.encode())
    while ...:
        port = int.from_bytes(h.digest()[:2], 'big')
        if port >= 1024:
            return port
        h.update('salt!'.encode())


class Device(Looper):
    """A device to interact with the robocluster network."""

    def __init__(self, name, group, network=None, context=None):
        """
        Initialize the device.

        Args:
            name (str): A name to identify the device by.
            group (str): Used to select the multicast address.
                In order for devices to talk to each other,
                they must be in the same group.
            network (str): IPv4 network to broadcast on (default 0.0.0.0/0)
            loop (asyncio.AbstractEventLoop, optional): Event loop to use.
                Defaults to the current event loop.
        """
        self.context = context or Context.instance()
        self.context._ready.wait()
        super().__init__(self.context.loop)

        if network is None:
            network = '0.0.0.0/0'
        port = group_to_port(group)
        self._member = Member(name, network, port, loop=self.loop)

        self._storage = AttributeDict()

    @property
    def name(self):
        """Name of the device."""
        return self._member.name

    @property
    def storage(self):
        """
        Local device storage.

        Use this to store arbitrary data that can be accessed from multiple
        tasks or callbacks.
        """
        return self._storage

    async def send(self, dest, endpoint, data):
        """
        Directly send data to another device.

        Args:
            dest (str): The device name to send to.
            endpoint (str): The endpoint to send to on destination device
            data: Any arbitrary data that can be handled by the transport.
        """
        await self._member.send(dest, endpoint, data)

    async def publish(self, topic, data):
        """
        Publish to topic.

        Args:
            topic (str): The topic, or event name to broadcast.
            data: Any arbitrary data that can be encoded and sent
                over the network. For the default json encoding,
                dictionaries are a good way to package data.
            port (str, list, optional): Specify which ports to publish to.
                Ports are identified by their name as a string.
                You can also provide a list of port names to
                publish over multiple ports.
                Defaults to 'multicast'.
        """
        await self._member.publish(topic, data)

    def on(self, event, callback=None):
        """
        Add a callback for an event.

        This function can be used as a decorator or as a standard function.
        Example::

            @device.on('other-device/hello')
            async def callback(event, data):
                print(event, data)

        Args:
            event (str): The event name to react to.
                You can use file globbing syntax to subscribe
                to multiple events: '*/heartbeat', 'important/*'
            port (str, list, optional): Specify which ports to listen over.
                Ports are identified by their name as a string.
                You can also provide a list of port names to
                listen to multiple ports.
                Defaults to None, which listens to all ports.
        """
        def decorator(callback):
            peer, _, endpoint = event.partition('/')
            if endpoint:
                self._member.subscribe(peer, endpoint, callback)
            else:
                # peer is actually the endpoint
                self._member.on_recv(peer, callback)
            return callback

        if callback is None:
            return decorator
        return decorator(callback)

    async def request(self, dest, endpoint, *args, **kwargs):
        """
        Request data from another device.

        Args:
            dest (str): The device name to request data from.
            endpoint (str): The endpoint to request.
            *args: Arguments passed to the endpoint.
            **kwargs: Keyword Arguments passed to the endpoint.

        Return:
            The return value of the endpoint that you requested.
        """
        return await self._member.request(dest, endpoint, *args, **kwargs)

    def on_request(self, endpoint, callback=None):
        """Add a callback for a request."""
        def decorator(callback):
            self._member.on_request(endpoint, callback)
            return callback

        if callback is None:
            return decorator
        return decorator(callback)

    def task(self, task):
        """
        Create a background task.

        This is a decorator function and can be used as follows::

            @device.task
            async def setup_task():
                ...

        This would register the setup_task coroutine to be ran
        by the device when the device is started.
        """
        coro = as_coroutine(task)
        self.create_task(coro)
        return task

    def every(self, duration):
        """
        Create a background task that runs every duration.
        Equivilent to::

            @device.task
            async def loop():
                while True:
                    # do things
                    ...
                    device.sleep(duration)

        Args:
            duration (str, int): How long to sleep in between loops.
                Takes the same form as :func:`~robocluster.util.duration_to_seconds`.

        """
        duration = duration_to_seconds(duration)
        def _decorator(func):
            coro = as_coroutine(func)
            @wraps(func)
            async def _wrapper():
                while True:
                    await coro()
                    await self.sleep(duration)
            self.create_daemon(_wrapper)
            return func
        return _decorator

    def start(self):
        """Start device."""
        super().start()
        self._member.start()

    def stop(self):
        """Stop device."""
        self._member.stop()
        super().stop()

    def wait(self):
        """Wait for device context to exit."""
        self.context.wait()

class Context(threading.Thread):
    __DEFAULT = None

    @staticmethod
    def instance():
        if Context.__DEFAULT is None:
            Context.__DEFAULT = Context()
            Context.__DEFAULT.start()
        return Context.__DEFAULT

    def __init__(self):
        super().__init__(daemon=True)
        self.loop = asyncio.new_event_loop()
        self._ready = threading.Event()

    def run(self):
        asyncio.set_event_loop(self.loop)
        self._ready.set()
        try:
            self.loop.run_forever()
        except:
            for task in asyncio.Task.all_tasks(loop=self.loop):
                task.cancel()
                with suppress(asyncio.CancelledError):
                    self.loop.run_until_complete(task)
            raise

    def wait(self):
        try:
            self.join()
        except KeyboardInterrupt:
            pass
