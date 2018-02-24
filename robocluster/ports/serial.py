import json

import pyvesc
import serial
import serial_asyncio

from .base import Port
from ..util import debug
from ..message import Message

class SerialPort(Port):
    """Handles reading and writing to a serial device"""
    def __init__(self, name, encoding='json', baudrate=115200, loop=None, disable_receive_loop=False):
        self._loop = loop if loop else asyncio.get_event_loop()
        self._usb_path = name
        self.name = name
        self._baudrate = baudrate
        self._reader = None  # once initialized, an asyncio.StreamReader
        self._writer = None  # once initialized, an asyncio.StreamWriter
        self.encoding = encoding
        self._loop.create_task(self._init_serial())
        super().__init__(loop=self._loop)

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

    async def _recv(self):
        """Read a single byte from the serial device."""
        if not self._reader:
            raise RuntimeError("Serial reader not initialized yet")
        try:
            _message = None
            if self.encoding == 'json':
                pkt = await self._reader.readline()
                _message = Message.from_string(pkt.strip().decode())
                if _message.type == 'heartbeat':
                    self.name = _message.source
            elif self.encoding == 'vesc':
                # Taken from Roveberrypy
                def to_int(b):
                    return int.from_bytes(b, byteorder='big')
                header = await self._reader.read(1)
                # magic VESC header must be 2 or 3
                if not to_int(header) == 2 or to_int(header) == 3:
                    raise RuntimeError('Got invalide VESC message')
                length = await self._reader.read(to_int(header) - 1)
                packet = await self._reader.read(to_int(length) + 4)
                msg, _ = pyvesc.decode(header + length + packet)
                if msg.__class__.__name__ == 'ReqSubscription':
                    self.name = msg.subscription
                    _message = Message( #TODO: How should message type be determined?
                        self.name,
                        'heartbeat',
                        {'source': self.name,
                         'listen': 'none'}
                    )
                else:
                    _message = Message( #TODO: How should message type be determined?
                        self.name,
                        'publish',
                        {'topic':msg.__class__.__name__,
                         'data': msg}
                    )
            else:
                raise RuntimeError('Encoding is not supported')
            debug("Got packet {}".format(_message))
            return _message, _message.source
        except ValueError:
            return None, None
        except serial.serialutil.SerialException:
            print('serial disconnect')
            self._reader = None
            while self._reader is None:
                await self._init_serial()
            return await self._recv()

    async def send(self, msg):
        """Write a packet to the port"""
        if not self._writer:
            raise RuntimeError("Serial writer not initialized yet")
        debug("Sending packet {}".format(msg))
        if self.encoding == 'json':
            return self._writer.write(msg.encode())
        elif self.encoding == 'vesc':
            return self._writer.write(pyvesc.encode(msg))
        else:
            raise RuntimeError('Encoding not supported')

