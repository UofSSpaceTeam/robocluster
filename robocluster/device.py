"""Message passing for robocluster."""

import asyncio
from collections import defaultdict
from contextlib import suppress
from fnmatch import fnmatch
from functools import wraps
from threading import Thread

from .util import duration_to_seconds, as_coroutine, debug
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

        self.events['*SEND_REQUEST'].append({
            'task': self.on_send_request,
            'port': ['multicast']
        })

        self.events['*SEND_CONFIRM'].append({
            'task': self.on_send_confirm,
            'port': [self.name+'_tcp']
        })

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

    async def send(self, dest, topic, data):
        if dest not in self.ports:
            self.create_egress_tcp(dest)
        packet = {
            'event': '{}/{}'.format(self.name, topic),
            'data': data
        }
        await self.ports[dest].write(packet)

    async def request(self, dest, topic):
        event_name = '{}/{}'.format(dest, topic)
        await self.send(dest, topic, None)
        future = asyncio.Future(loop=self._loop)
        @self.on(event_name)
        async def return_data(event, data):
            future.set_result(data)
            self.events[event_name] = None
        await future
        return future.result()

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

    def create_serial(self, usb_path, encoding=transport):
        """Create a new SerialDevice."""
        self.ports[usb_path] = SerialPort(
            name=usb_path,
            group=None,
            encoding=encoding,
            loop=self._loop,
            packet_queue=self._packet_queue
        )
        self._loop.create_task(self.ports[usb_path].enable())

    def create_ingress_tcp(self, device_name, encoding=transport):
        self.ports[device_name] = IngressTcpPort(
            name=device_name,
            encoding=encoding,
            packet_queue=self._packet_queue,
            loop=self._loop
        )
        self._loop.create_task(self.ports[device_name].enable())

    def create_egress_tcp(self, device_name, encoding=transport):
        self.ports[device_name] = EgressTcpPort(
            name=device_name,
            encoding=encoding,
            loop=self._loop
        )
        async def send_request():
            async with self.ports[self.name+'_tcp'] as ingress:
                sockname = ingress.getsockname()
                await self.publish('SEND_REQUEST', {
                    'requested-device': device_name,
                    'sender-address': sockname[0],
                    'sender-port': sockname[1],
                    'sender-name': self.name,
                    'encoding': encoding
                })
        self._loop.create_task(send_request())

    async def on_send_request(self, event, data):
        if data['requested-device'] == self.name:
            sender_name = data['sender-name']
            # Create a new egress port for the sender
            self.ports[sender_name] = EgressTcpPort(
                name=sender_name,
                encoding=data['encoding'],
                loop=self._loop
            )
            async with self.ports[self.name+'_tcp'] as ingress:
                sockname = ingress.getsockname()
                # enable the port to the sender
                await self.ports[sender_name].enable(
                    host=data['sender-address'],
                    port=data['sender-port']
                )
                # Send them our connection information
                await self.ports[sender_name].write({
                    'event': 'SEND_CONFIRM',
                    'data': {
                        'name': self.name,
                        'address': sockname[0],
                        'port': sockname[1]
                    }
                })

    async def on_send_confirm(self, event, data):
        await self.ports[data['name']].enable(
            host=data['address'],
            port=data['port']
        )

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
