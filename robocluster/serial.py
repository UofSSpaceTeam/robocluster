"""Handles comunication to serial devices."""

import asyncio
import json
from collections import defaultdict

import pyvesc
import serial_asyncio

from .util import as_coroutine

BAUDRATE = 115200


class SerialDevice:
    """A serial device that can be integrated with the robocluster network."""

    def __init__(self, usb_path, baudrate=BAUDRATE, encoding='json', loop=None):
        """Initialize serial device."""
        self._loop = loop if loop else asyncio.get_event_loop()
        self._encoding = encoding
        self._reader = None  # once initialized, an asyncio.StreamReader
        self._writer = None  # once initialized, an asyncio.StreamWriter
        self._usb_path = usb_path
        self._baudrate = baudrate
        self.events = defaultdict(list)

    def __str__(self):
        """Return string representation of a SerialDevice."""
        return 'SerialDevice(usb_path={}, baudrate={}, encoding={})'.format(
            self._usb_path,
            self._baudrate,
            self._encoding,
        )

    async def __aenter__(self):
        """Enter async context manager."""
        r, w = await serial_asyncio.open_serial_connection(
            loop=self._loop,
            url=self._usb_path,
            baudrate=self._baudrate
        )
        self._reader, self._writer = r, w
        return self

    async def __aexit__(self, *exc):
        """Exit async context manager."""
        pass

    @property
    def usb_path(self):
        """Path to the usb device."""
        return self._usb_path

    @property
    def initialized(self):
        """Return if the StreamReader and StreamWriter are initialized."""
        return self._reader and self._writer

    def read_byte(self):
        """Read a single byte from the serial device."""
        if not self._reader:
            raise RuntimeError("Serial reader not initialized yet")
        return self._reader.read(1)

    async def read_packet(self):
        """Read a json packet from the serial device."""
        if not self._reader:
            raise RuntimeError("Serial reader not initialized yet")
        if self._encoding == 'json':
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
        elif self._encoding == 'vesc':
            # Taken from Roveberrypy
            def to_int(b):
                return int.from_bytes(b, byteorder='big')
            header = await self._reader.read(1)
            # magic VESC header must be 2 or 3
            if not to_int(header) == 2 or to_int(header) == 3:
                return None  # raise error maybe?
            length = await self._reader.read(to_int(header) - 1)
            packet = await self._reader.read(to_int(length) + 4)
            msg, _ = pyvesc.decode(head + length + packet)
            return {
                'event': msg.__class__.__name__,
                'data': msg
            }

        raise RuntimeError('Packet format type not supported')

    async def write_packet(self, data_object):
        """Write a packet (or bytes) to the serial device."""
        if not self._writer:
            raise RuntimeError("Serial writer not initialized yet")
        if self._encoding == 'raw':
            return self._writer.write(data_object)
        elif self._encoding == 'utf8':
            return self._writer.write(data_object.encode())
        elif self._encoding == 'json':
            return self._writer.write(json.dumps(data_object).encode())
        elif self._encoding == 'vesc':
            return self._writer.write(pyvesc.encode(data_object))
        raise RuntimeError('Packet format type not supported')

    def on(self, event):
        """Add a callback for an event."""
        def _decorator(callback):
            coro = as_coroutine(callback)
            self.events[event].append(coro)
            return callback
        return _decorator
