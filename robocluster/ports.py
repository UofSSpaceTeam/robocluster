import asyncio
import json

import pyvesc
import serial_asyncio

from .net import Socket, key_to_multicast
from .util import debug

class Port:
    """Provides a high level wrapper for arbitrary hardware protocols"""

    #TODO: Define a good way to standardize __init__ while also initializing
    #      parameters specific to a Port type (baudrate for serial,
    #      group for multicast, etc).

    async def read(self):
        raise NotImplementedError("Port is an abstract class")

    def write(self, packet):
        raise NotImplementedError("Port is an abstract class")

    async def _send_task(self):
        raise NotImplementedError("Port is an abstract class")

    async def _receive_task(self):
        raise NotImplementedError("Port is an abstract class")

    async def enable(self):
        """
        Starts the receive_task and send_task.
        It is a coroutine in case the interface needs to call
        other asynchronous coroutines during initialization.
        """
        self._loop.create_task(self._send_task())
        self._loop.create_task(self._receive_task())


class MulticastPort(Port):
    """Provides a high level wrapper for a multicast socket"""

    def __init__(self, name, group, encoding, packet_queue, loop=None):
        self.name = name
        self._loop = loop if loop else asyncio.get_event_loop()
        self._packet_queue = packet_queue

        address = key_to_multicast(group)
        self._sender = Socket(
                address,
                transport=encoding,
                loop=loop
        )
        self._send_queue = asyncio.Queue(loop=self._loop)

        self._receiver = Socket(
                address,
                transport=encoding,
                loop=self._loop
        )
        self._receiver.bind()

    async def read(self):
        """Read data from the port"""
        raise NotImplementedError("Can't read from a multicast port")

    def write(self, packet):
        """Write a packet to the port"""
        return self._send_queue.put(packet)

    async def _send_task(self):
        """Send packets in the send queue."""
        while True:
            packet = await self._send_queue.get()
            debug("Sending packet: {}".format(packet))
            await self._sender.send(packet)

    async def _receive_task(self):
        """Recieve packets and notify the upstream Device"""
        while True:
            packet, _ = await self._receiver.receive()
            packet['port'] = 'multicast'
            debug("Got packet: {}".format(packet))
            await self._packet_queue.put(packet)

class IngressTcpPort(Port):

    def __init__(self, name, encoding, packet_queue, loop=None):
        self.name = name
        self._loop = loop if loop else asyncio.get_event_loop()
        self._packet_queue = packet_queue
        self._encoding = encoding
        self._sockname = None  # Connection information address:port

    async def __aenter__(self):
        if self._sockname is None:
            await self.enable()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def _receive_task(self, reader, writer):
        debug("TCP receive_task Running")
        while True:
            _packet = {}
            if self._encoding == 'json':
                pkt = ''
                curleystack = 0
                squarestack = 0
                done_reading = False
                while not done_reading:
                    b = await reader.read(1)
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
            else:
                raise RuntimeError("Encoding not supported yet")
            _packet['port'] = self.name
            debug("Got packet {}".format(_packet))
            await self._packet_queue.put(_packet)

    async def enable(self):
        self._server = await asyncio.start_server(
            self._receive_task,
            'localhost', # TODO bind to all addresses?
            0,  # Let the OS find a free port
            loop=self._loop
        )
        self._sockname = self._server.sockets[0].getsockname()

    def getsockname(self):
        return self._sockname


class EgressTcpPort(Port):

    def __init__(self, name, encoding, loop=None):
        self.name = name
        self._loop = loop if loop else asyncio.get_event_loop()
        self._encoding = encoding
        self._host = None
        self._port = None
        self._send_queue = asyncio.Queue(loop=self._loop)

    def write(self, packet):
        debug("Egress TCP Submitting packet to send: {}".format(packet))
        return self._send_queue.put(packet)

    async def _send_task(self):
        if not self._writer:
            raise RuntimeError("Egress TCP writer not initialized yet")
        debug("Egress TCP Send task running")
        while True:
            packet = await self._send_queue.get()
            debug("Egress TCP Sending packet {}".format(packet))
            if self._encoding == 'raw':
                await self._writer.write(packet)
            elif self._encoding == 'utf8':
                await self._writer.write(packet.encode())
            elif self._encoding == 'json':
                self._writer.write(json.dumps(packet).encode())
            else:
                raise RuntimeError('Packet format type not supported')

    async def enable(self, host, port):
        self._host = host
        self._port = port
        r, w = await asyncio.open_connection(
                host=self._host,
                port=self._port,
                loop=self._loop
        )
        self._reader, self._writer = r, w
        debug("Egress TCP reader and writer initialized")
        self._loop.create_task(self._send_task())

class SerialPort(Port):

    def __init__(self, name, group, encoding, loop, packet_queue):
        self.name = name
        self._loop = loop
        self._packet_queue = packet_queue
        self._reader = None  # once initialized, an asyncio.StreamReader
        self._writer = None  # once initialized, an asyncio.StreamWriter
        self._encoding = encoding
        self._usb_path = name
        self._baudrate = 115200
        self._send_queue = asyncio.Queue(loop=self._loop)

    async def _init_serial(self):
        """Enter async context manager."""
        r, w = await serial_asyncio.open_serial_connection(
            loop=self._loop,
            url=self._usb_path,
            baudrate=self._baudrate
        )
        self._reader, self._writer = r, w
        debug("Serial reader and writer initialized")

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
            if self._encoding == 'raw':
                await self._writer.write(packet)
            elif self._encoding == 'utf8':
                await self._writer.write(packet.encode())
            elif self._encoding == 'json':
                await self._writer.write(json.dumps(packet).encode())
            elif self._encoding == 'vesc':
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
            _packet = {}
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
                _packet = json.loads(pkt)
            elif self._encoding == 'vesc':
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
            _packet['port'] = self.name
            debug("Got packet {}".format(_packet))
            await self._packet_queue.put(_packet)

    async def enable(self):
        """
        Starts the receive_task and send_task
        and initializes reader and writer
        """
        await self._init_serial()
        await super().enable()
