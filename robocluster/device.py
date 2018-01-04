"""Message passing for robocluster."""

import asyncio
from collections import defaultdict
from contextlib import suppress
from fnmatch import fnmatch
from functools import wraps
from threading import Thread

from .util import duration_to_seconds, as_coroutine
from .ports import MulticastPort, SerialPort, EgressTcpPort, IngressTcpPort

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

class Device:
    """A device to interact with the robocluster network."""

    transport = 'json'

    def __init__(self, name, group, loop=None):
        """Initialize the device."""
        self.name = name
        self.events = defaultdict(list)

        self._thread = None
        self._loop = loop if loop else asyncio.new_event_loop()

        self._packet_queue = asyncio.Queue(loop=self._loop)

        self.ports = {
                'multicast': MulticastPort(name, group, self.transport,
                    self._packet_queue, self._loop)
        }
        self.create_ingress_tcp(self.name+'_tcp')
        self._loop.create_task(self.ports['multicast'].enable())

        self.__storage = AttributeDict()

    @property
    def storage(self):
        """Local device storage"""
        return self.__storage

    async def publish(self, topic, data, port='multicast'):
        """Publish to topic."""
        packet = {
            'event': '{}/{}'.format(self.name, topic),
            'data': data,
        }
        if port == '*':
            for p in self.ports:
                await p.write(packet)
        else:
            if isinstance(port, str):
                port = [port]
            for p in port:
                await self.ports[p].write(packet)

    def on(self, event, ports=None):
        """Add a callback for an event."""
        if isinstance(ports, str):
            ports = [ports]
        def _decorator(callback):
            coro = {
                'task': as_coroutine(callback),
                'port': ports
            }
            self.events[event].append(coro)
            return callback
        return _decorator

    def task(self, task):
        """Create a background task."""
        coro = as_coroutine(task)
        self._loop.create_task(coro())
        return task

    def every(self, duration):
        """Create a background task that runs every duration."""
        def _decorator(func):
            @wraps(func)
            async def _wrapper():
                while True:
                    coro = as_coroutine(func)
                    await coro()
                    await self.sleep(duration)
            self.task(_wrapper)
            return func
        return _decorator

    def sleep(self, duration):
        """Sleep the device."""
        seconds = duration_to_seconds(duration)
        return asyncio.sleep(seconds, loop=self._loop)

    async def callback_handler(self):
        """Recieve packets and call the appropriate callbacks."""
        while True:
            packet = await self._packet_queue.get()
            event, data = packet['event'], packet['data']
            for key, callbacks in self.events.items():
                if not fnmatch(event, key):
                    continue
                for callback in callbacks:
                    if callback['port'] is None or packet['port'] in callback['port']:
                        self._loop.create_task(callback['task'](event, data))

    def create_serial(self, usb_path, encoding='json'):
        """Create a new SerialDevice."""
        self.ports[usb_path] = SerialPort(
            name=usb_path,
            group=None,
            encoding=encoding,
            loop=self._loop,
            packet_queue=self._packet_queue
        )
        self._loop.create_task(self.ports[usb_path].enable())

    def create_ingress_tcp(self, device_name, encoding='json'):
        self.ports[device_name] = IngressTcpPort(
            name=device_name,
            encoding=encoding,
            packet_queue=self._packet_queue,
            loop=self._loop
        )
        self._loop.create_task(self.ports[device_name].enable())

    def create_egress_tcp(self, device_name, encoding='json'):
        address = 'localhost'
        port = 9000
        self.ports[device_name] = EgressTcpPort(
            name=device_name,
            host=address,
            port=port,
            encoding=encoding,
            loop=self._loop
        )
        self._loop.create_task(self.ports[device_name].enable())

    def start(self):
        """Start device."""
        if self._thread:
            raise RuntimeError('device already running')
        self._thread = Thread(target=self._thread_target)
        self._thread.start()

    def _thread_target(self):
        """Target for thread to run event loop in background."""
        loop = self._loop
        asyncio.set_event_loop(loop)

        loop.create_task(self.callback_handler())
        loop.run_forever()

        for task in asyncio.Task.all_tasks(loop=loop):
            task.cancel()
            with suppress(asyncio.CancelledError):
                loop.run_until_complete(task)

    def run(self):
        """Run device in foreground."""
        try:
            self.start()
            self.wait()
        except KeyboardInterrupt:
            self.stop()
            raise

    def wait(self):
        """Wait until device exits."""
        if self._thread:
            self._thread.join()

    def stop(self):
        """Stop running device."""
        if not self._thread:
            raise RuntimeError('device not running')
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join()
        self._thread = None
