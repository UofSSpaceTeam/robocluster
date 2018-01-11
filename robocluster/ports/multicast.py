import asyncio

from .base import Port
from ..net import Socket, key_to_multicast
from ..util import debug


class MulticastPort(Port):
    """Provides a high level wrapper for a multicast socket"""

    def __init__(self, name, group, encoding, packet_queue, loop=None):
        """
        Initialize a multicast port.

        Args:
            name (str): The name to identify the port by.
            group (str): Used to generate the multicast address and port.
            encoding (str): How to structure the data, json, utf8, etc.
            packet_queue (asyncio.Queue): Queue to put incomming messages into.
            loop (asyncio.AbstractEventLoop, optional):
                The event loop to run on. Defaults to the current event loop.
        """
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

