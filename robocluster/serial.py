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

    def __str__(self):
        """String representation of a SerialDevice"""
        return 'SerialDevice(usbpath={}, baudrate={}, pktformat={})'.format(
                self._usbpath, self._baudrate, self._format
                )

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
        """Read a json packet from the serial device."""
        if not self._reader:
            raise RuntimeError("Serial reader not initialized yet")
        if self._format == 'json':
            pkt = ''
            curleystack = 0
            squarestack = 0
            done_reading = False
            while not done_reading:
                b = await self._reader.read(1)
                b = b.decode()
                if b == '{':
                    curleystack += 1
                elif b == '}':
                    curleystack -= 1
                elif b == '[':
                    squarestack += 1
                elif b == ']':
                    squarestack -= 1
                pkt += b
                if curleystack == 0 and squarestack == 0:
                    done_reading = True
            return json.loads(pkt)

        raise RuntimeError('Packet format type not supported')

    async def write_packet(self, data_object):
        """Write a packet (or bytes) to the serial device"""
        if not self._writer:
            raise RuntimeError("Serial writer not initialized yet")
        if self._format == 'raw':
            return self._writer.write(data_object)
        elif self._format == 'utf8':
            return self._writer.write(data_object.encode())
        elif self._format == 'json':
            return self._writer.write(json.dumps(data_object).encode())
        raise RuntimeError('Packet format type not supported')

    def on(self, event):
        """Add a callback for an event."""
        def _decorator(callback):
            coro = as_coroutine(callback)
            self.events[event].append(coro)
            return callback
        return _decorator
