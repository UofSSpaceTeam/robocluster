import asyncio
from .net import Socket, key_to_multicast

class MulticastPort:
    """Provides a high level wrapper for a multicast socket"""

    def __init__(self, name, group, transport, loop, packet_queue):
        self.name = name
        self._loop = loop
        self._packet_queue = packet_queue

        address = key_to_multicast(group)
        self._sender = Socket(
                address,
                transport=transport,
                loop=loop
        )
        self._send_queue = asyncio.Queue(loop=self._loop)

        self._receiver = Socket(
                address,
                transport=transport,
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
            await self._sender.send(packet)

    async def _receive_task(self):
        """Recieve packets and notify the upstream Device"""
        while True:
            packet, _ = await self._receiver.receive()
            await self._packet_queue.put(packet)

    def enable(self):
        """Starts the receive_task and send_task"""
        self._loop.create_task(self._send_task())
        self._loop.create_task(self._receive_task())
