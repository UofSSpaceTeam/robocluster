import asyncio
import json
import socket

from .base import Port
from ..net import AsyncSocket, key_to_multicast
from ..util import debug


class MulticastPort(Port):
    """Provides a high level wrapper for a multicast socket"""

    def __init__(self, name, group, packet_queue, encoding='json', loop=None):
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

        self._group, self._port = key_to_multicast(group)

        self._sender = AsyncSocket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            loop=self._loop
        )
        self._send_queue = asyncio.Queue(loop=self._loop)

        self._multicast = AsyncSocket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            loop=self._loop
        )
        self._multicast.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._multicast.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self._multicast.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_TTL, 1)
        self._multicast.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_LOOP, 1)
        self._multicast.setsockopt(
            socket.SOL_IP, socket.IP_ADD_MEMBERSHIP,
            socket.inet_aton(self._group) + socket.inet_aton('0.0.0.0')
        )
        self._multicast.bind(('0.0.0.0', self._port))

    async def read(self):
        """Read data from the port"""
        raise NotImplementedError("Can't read from a multicast port")

    async def write(self, bytes):
        """Write a packet to the port"""
        return self._send_queue.put(bytes)

    async def send(self, packet):
        raw = json.dumps(packet).encode()
        return await self.write(raw)

    async def _send_task(self):
        """Send packets in the send queue."""
        while True:
            packet = await self._send_queue.get()
            debug("Sending packet: {}".format(packet))
            await self.sendto(packet, (self._group, self._port))

    async def receive(self):
        raw, addr = await self._multicast.recvfrom(1024)
        try:
            packet = json.loads(raw.decode())
            return packet, addr
        except json.JSONDecodeError:
            return None, addr

    async def _receive_task(self):
        """Recieve packets and notify the upstream Device"""
        while True:
            packet, _ = await self.receive()
            packet['port'] = 'multicast'
            debug("Got packet: {}".format(packet))
            await self._packet_queue.put(packet)

