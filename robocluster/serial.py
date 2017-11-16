import serial_asyncio
import asyncio
import json
from collections import defaultdict

from .util import as_coroutine

BAUDRATE = 115200


class SerialDevice:
    """
    A serial device that can optionally be integrated
    with the robocluster network.
    """

    def __init__(self, usbpath, baudrate=BAUDRATE, pktformat='json', loop=None):
        self._loop = loop if loop else asyncio.get_event_loop()
        self._format = pktformat
        self._reader = None  # once initialized, an asyncio.StreamReader
        self._writer = None  # once initialized, an asyncio.StreamWriter
        self._usbpath = usbpath
        self._baudrate = baudrate
        self.events = defaultdict(list)

    async def __aenter__(self):
        """Enter context manager and initialize the StreamReader and StreamWriter."""
        self._reader, self._writer = await serial_asyncio.open_serial_connection(
                loop=self._loop,
                url=self._usbpath,
                baudrate=self._baudrate)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    def isInitialized(self):
        """Checks if the StreamReader and StreamWriter are initialized"""
        return self._reader and self._writer

    def read_byte(self):
        """Read a single byte from the serial device"""
        if not self._reader:
            raise RuntimeError("Serial reader not initialized yet")
        return self._reader.read(1)

    async def read_packet(self):
        """
        Read a json packet from the serial device.
        Assumes the packet is a single dictionary and there
        are no nested dictionaries.
        """
        if not self._reader:
            raise RuntimeError("Serial reader not initialized yet")
        if self._format == 'json':
            pkt = await self._reader.readuntil(b'}')
            return json.loads(pkt)

        raise RuntimeError('Packet format type not supported')

    def on(self, event):
        """Add a callback for an event."""
        def _decorator(callback):
            coro = as_coroutine(callback)
            self.events[event].append(coro)
            return callback
        return _decorator
