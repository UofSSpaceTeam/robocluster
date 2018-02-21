import json

import pyvesc
import serial
import serial_asyncio

from ..util import debug

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
        self._loop.create_task(self._init_serial(disable_receive_loop))
        super().__init__(loop=loop)

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

        except serial.serialutil.SerialException:
            print('serial disconnect')
            self._reader = None
            while self._reader == None:
                await self._init_serial()

    def send(self, msg):
        """Write a packet to the port"""
        if not self._writer:
            raise RuntimeError("Serial writer not initialized yet")
        debug("Sending packet {}".format(packet))
        self._writer.write(msg.encode())

