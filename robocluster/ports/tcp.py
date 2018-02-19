import socket

from ..net import AsyncSocket
from .base import Port, BUFFER_SIZE
from ..util import ip_info
from ..message import Message

class TcpConnection(Port):

    def __init__(self, sock, loop=None):
        self._socket = sock
        super().__init__(loop=loop)

    @classmethod
    async def from_addr(cls, host, port, loop=None):
        """Connect to a listening server by host and port."""
        family, host = ip_info(host)
        sock = AsyncSocket(family, socket.SOCK_STREAM, loop=loop)
        await sock.connect((str(host), port))
        return cls(sock)

    async def send(self, msg):
        """Write a message to the connection."""
        return await self._socket.send(msg.encode())

    async def _recv(self):
        """Read a message from the connection."""
        b = await self._socket.recv(BUFFER_SIZE)
        msg = Message.from_bytes(b)
        return msg, msg.source

    def stop(self):
        super().stop()
        self._socket.close()

