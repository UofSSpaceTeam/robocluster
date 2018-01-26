import asyncio
import json

import pyvesc
import serial
import serial_asyncio

from .device import Device
from .util import debug
from .router import Message

class SerialConnection():
    """Handles reading and writing to a serial device"""
    def __init__(self, name, encoding='json', baudrate=115200, loop=None, disable_receive_loop=False):
        self._loop = loop if loop else asyncio.get_event_loop()
        self._usb_path = name
        self.name = name
        self._baudrate = baudrate
        self._reader = None  # once initialized, an asyncio.StreamReader
        self._writer = None  # once initialized, an asyncio.StreamWriter
        self.encoding = encoding
        self._send_queue = asyncio.Queue(loop=self._loop)
        self._loop.create_task(self._init_serial(disable_receive_loop))
        self.packet_callback = None

    async def _init_serial(self, disable_receive_loop):
        """Initialize the StreamReader and StreamWriter."""
        try:
            r, w = await serial_asyncio.open_serial_connection(
                loop=self._loop,
                url=self._usb_path,
                baudrate=self._baudrate
            )
            self._reader, self._writer = r, w
            debug("Serial reader and writer initialized")
            if not disable_receive_loop:
                self._loop.create_task(self._receive_task())
            self._loop.create_task(self._send_task())
        except serial.serialutil.SerialException:
            print('USB path not found')
            await asyncio.sleep(0.2)

    async def read(self, num_bytes=1):
        """Read a single byte from the serial device."""
        if not self._reader:
            raise RuntimeError("Serial reader not initialized yet")
        return self._reader.read(num_bytes)


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
                self._writer.write(packet)
            elif self.encoding == 'utf8':
                self._writer.write(packet.encode())
            elif self.encoding == 'json':
                self._writer.write(json.dumps(packet).encode())
            elif self.encoding == 'vesc':
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
                _message = None
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
                    _message = Message.from_string(pkt)
                    if _message.type == 'heartbeat':
                        self.name = _message.source
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
                    _message = Message( #TODO: How should message type be determined?
                        self.name,
                        'publish',
                        {'topic':msg.__class__.__name__,
                         'data': msg}
                    )
                else:
                    raise RuntimeError('Encoding is not supported')
                debug("Got packet {}".format(_message))
                if self.packet_callback is not None:
                    await self.packet_callback(_message)
            except serial.serialutil.SerialException:
                print('serial disconnect')
                self._reader = None
                while self._reader == None:
                    await self._init_serial()


class SerialDevice(Device):
    """Device that exposes a serial device to the robocluster network."""

    def __init__(self, name, group, loop=None, encoding='json', disable_receive_loop=False):
        super().__init__(name, group, loop=loop)
        self.serial_connection = SerialConnection(name,
                encoding=encoding, loop=self._loop,
                disable_receive_loop=disable_receive_loop)
        self.serial_connection.packet_callback = self.handle_packet
        self._router.on_message(self.forward_packet)

    async def handle_packet(self, message):
        """Forward messages from serial to robocluster network."""
        print(message)
        if message.type == 'heartbeat':
            self.name = message.source
            self._router.name = self.name
        await self._router.route_message(message)

    async def forward_packet(self, packet):
        """Forwards messages from robocluster network to serial device."""
        await self.serial_connection.write(packet.to_json())

    async def write(self, data):
        """Write to the serial device."""
        await self.serial_connection.write(data)

    async def read(self, num_bytes=1):
        """Read a byte from the serial device"""
        return self.serial_connection.read(num_bytes)
