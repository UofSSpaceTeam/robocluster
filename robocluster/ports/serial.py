import asyncio
import json

import pyvesc
import serial
import serial_asyncio

from .base import Port
from ..util import debug


class SerialPort(Port):
    """Wrapper for USB or USRT serial connections."""

    def __init__(self, name, encoding, packet_queue, loop=None):
        """
        Initialize the serial port.

        Args:
            name (str): The name to identify the port by.
            group (str): unused, please remove...
            encoding (str): How to structure the data, json, vesc, etc.
            packet_queue (asyncio.Queue): Queue to put incomming messages into.
            loop (asyncio.AbstractEventLoop, optional):
                The event loop to run on. Defaults to the current event loop.
        """
        self.name = name
        self._loop = loop if loop else asyncio.get_event_loop()
        self._packet_queue = packet_queue
        self._reader = None  # once initialized, an asyncio.StreamReader
        self._writer = None  # once initialized, an asyncio.StreamWriter
        self.encoding = encoding
        self._usb_path = name
        self._baudrate = 115200
        self._send_queue = asyncio.Queue(loop=self._loop)

    async def _init_serial(self):
        """Initialize the StreamReader and StreamWriter."""
        try:
            r, w = await serial_asyncio.open_serial_connection(
                loop=self._loop,
                url=self._usb_path,
                baudrate=self._baudrate
            )
            self._reader, self._writer = r, w
            debug("Serial reader and writer initialized")
        except serial.serialutil.SerialException:
            print('USB path not found')
            await asyncio.sleep(0.2)

    async def read(self):
        """Read a single byte from the serial device."""
        if not self._reader:
            raise RuntimeError("Serial reader not initialized yet")
        return self._reader.read(1)


    def write(self, packet):
        """Write a packet to the port"""
        debug("Submitting packet to send: {}".format(packet))
        return self._send_queue.put(packet)

    async def _send_task(self):
        """Write a packet (or bytes) to the serial device."""
        if not self._writer:
            raise RuntimeError("Serial writer not initialized yet")
        debug("Send task running")
        while True:
            packet = await self._send_queue.get()
            debug("Sending packet {}".format(packet))
            if self.encoding == 'raw':
                await self._writer.write(packet)
            elif self.encoding == 'utf8':
                await self._writer.write(packet.encode())
            elif self.encoding == 'json':
                await self._writer.write(json.dumps(packet).encode())
            elif self.encoding == 'vesc':
                # I don't know why I can't await the _writer in
                # this context, but can in others...
                self._writer.write(pyvesc.encode(packet))
            else:
                raise RuntimeError('Packet format type not supported')

    async def _receive_task(self):
        """Recieve packets and notify the upstream Device"""
        if not self._reader:
            raise RuntimeError("Serial reader not initialized yet")
        debug("Serial Receive task running")
        while True:
            try:
                _packet = {}
                if self.encoding == 'json':
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
                    _packet = json.loads(pkt)
                elif self.encoding == 'vesc':
                    # Taken from Roveberrypy
                    def to_int(b):
                        return int.from_bytes(b, byteorder='big')
                    header = await self._reader.read(1)
                    # magic VESC header must be 2 or 3
                    if not to_int(header) == 2 or to_int(header) == 3:
                        continue  # raise error maybe?
                    length = await self._reader.read(to_int(header) - 1)
                    packet = await self._reader.read(to_int(length) + 4)
                    msg, _ = pyvesc.decode(header + length + packet)
                    _packet = {
                        'event': msg.__class__.__name__,
                        'data': msg
                    }
                else:
                    raise RuntimeError('Encoding is not supported')
                _packet['port'] = self.name
                debug("Got packet {}".format(_packet))
                await self._packet_queue.put(_packet)
            except serial.serialutil.SerialException:
                print('serial disconnect')
                self._reader = None
                while self._reader == None:
                    await self._init_serial()

    async def enable(self):
        """
        Starts the receive_task and send_task
        and initializes reader and writer
        """
        await self._init_serial()
        await super().enable()
