import asyncio
import json

from .base import Port
from ..net import Socket
from ..util import debug


class IngressTcpPort(Port):
    """
    Wrapper for a TCP socket for incomming connections.

    Provides an asynchronous context manager interface.
    """

    def __init__(self, name, encoding, packet_queue, loop=None):
        """
        Initialize an ingress TCP port.

        Args:
            name (str): The name to identify the port by.
            encoding (str): How to structure the data, json, utf8, etc.
            packet_queue (asyncio.Queue): Queue to put incomming messages into.
            loop (asyncio.AbstractEventLoop, optional):
                The event loop to run on. Defaults to the current event loop.
        """
        self.name = name
        self._loop = loop if loop else asyncio.get_event_loop()
        self._packet_queue = packet_queue
        self.encoding = encoding
        self._sockname = None  # Connection information address:port

    async def __aenter__(self):
        if self._sockname is None:
            await self.enable()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def _receive_task(self, reader, writer):
        """Receive packets from the network and submit them to the device."""
        debug("TCP receive_task Running")
        while True:
            _packet = {}
            if self.encoding == 'json':
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
        """Enable the port and start the receive_task."""
        self._server = await asyncio.start_server(
            self._receive_task,
            'localhost', # TODO bind to all addresses?
            0,  # Let the OS find a free port
            loop=self._loop
        )
        self._sockname = self._server.sockets[0].getsockname()

    def getsockname(self):
        """Returns information about the socket connection."""
        return self._sockname


class EgressTcpPort(Port):
    """Wrapper for a TCP socket for outgoing connections."""

    def __init__(self, name, encoding, loop=None):
        """
        Initialize the port.

        Args:
            name (str): The name to identify the port by.
            encoding (str): How to structure the data, json, utf8, etc.
            loop (asyncio.AbstractEventLoop, optional):
                The event loop to run on. Defaults to the current event loop.
        """
        self.name = name
        self._loop = loop if loop else asyncio.get_event_loop()
        self.encoding = encoding
        self._host = None
        self._port = None
        self._send_queue = asyncio.Queue(loop=self._loop)

    def write(self, packet):
        """
        Schedule a new packet to be sent. This doesn't return once
        the packet is actually sent, it just puts it on a queue
        for the send_task to send it as soon as it's ready.
        """
        debug("Egress TCP Submitting packet to send: {}".format(packet))
        return self._send_queue.put(packet)

    async def _send_task(self):
        """Write packets to the tcp socket."""
        if not self._writer:
            raise RuntimeError("Egress TCP writer not initialized yet")
        debug("Egress TCP Send task running")
        while True:
            packet = await self._send_queue.get()
            debug("Egress TCP Sending packet {}".format(packet))
            if self.encoding == 'raw':
                await self._writer.write(packet)
            elif self.encoding == 'utf8':
                await self._writer.write(packet.encode())
            elif self.encoding == 'json':
                self._writer.write(json.dumps(packet).encode())
            else:
                raise RuntimeError('Packet format type not supported')

    async def enable(self, host, port):
        """Enable the port and start the send_task."""
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
