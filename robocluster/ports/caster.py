import socket
import struct
from contextlib import suppress

from .base import Port, BUFFER_SIZE
from ..net import AsyncSocket, key_to_multicast
from ..message import Message
from ..util import ip_info


class Multicaster(Port):
    def __init__(self, group, port, loop=None):
        """
        Initialize the multicaster.

        Arguments:
            group: multicast group to send and receive from.
            port: port to bind to.

        Optional Arguments:
            loop: event loop to use.
        """
        family, addr = ip_info(group)
        if not addr.is_multicast:
            raise ValueError('group is not multicast')

        self._group = str(addr), port

        sock = AsyncSocket(family, socket.SOCK_DGRAM, loop=loop)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        with suppress(AttributeError):
            # This is thrown on Linux
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        sock.bind(('', port))

        group_bin = socket.inet_pton(family, self._group[0])
        if family == socket.AF_INET6:
            mreq = group_bin + struct.pack('@I', socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)
            self._udp_send = sock
            self._udp_recv = sock
        elif family == socket.AF_INET:
            mreq = group_bin + struct.pack('=I', socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            # IPv4 does not allow sending from multicast bound socket
            self._udp_send = AsyncSocket(family, socket.SOCK_DGRAM, loop=loop)
            self._udp_recv = sock

        # We call this at the end so that the socket can be created before
        # the recv_daemon starts
        super().__init__(loop=loop)

    @property
    def address(self):
        """Address of the receiving socket."""
        return self._udp_recv.getsockname()

    async def _recv(self):
        msg, other = await self._udp_recv.recvfrom(BUFFER_SIZE)
        msg = Message.from_bytes(msg)
        return msg, other

    async def send(self, type, data):
        """Send a message on the multicast network."""
        msg = Message(self._uuid, type, data)
        return await self._udp_send.sendto(msg.encode(), self._group)

    def stop(self):
        """Stops multicaster."""
        super().stop()

        family = self._udp_recv.family
        group_bin = socket.inet_pton(family, self._group[0])
        if family == socket.AF_INET6:
            mreq = group_bin + struct.pack('@I', socket.INADDR_ANY)
            self._udp_recv.setsockopt(
                socket.IPPROTO_IPV6, socket.IPV6_LEAVE_GROUP, mreq)
            self._udp_recv.close()
        elif family == socket.AF_INET:
            mreq = group_bin + struct.pack('=I', socket.INADDR_ANY)
            self._udp_recv.setsockopt(
                socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, mreq)
            self._udp_recv.close()
            self._udp_send.close()


class Broadcaster(Port):
    """Caster on IPv4 broadcast."""

    MAGIC = b'\x46\xb4\x9a\x0d'  # used to make sure we parse our packets

    def __init__(self, port, loop=None):
        """
        Initialize the broadcaster.

        Arguments:
            port: port to bind to.

        Optional Arguments:
            loop: event loop to use.
        """
        self._address = '255.255.255.255', port

        sock = AsyncSocket(socket.AF_INET, socket.SOCK_DGRAM, loop=loop)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        with suppress(AttributeError):
            # This is thrown on Linux
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        sock.bind(('', port))
        self._udp = sock

        # We call this at the end so that the socket can be created before
        # the recv_daemon starts
        super().__init__(loop=loop)

    @property
    def address(self):
        """Address of the receiving socket."""
        return self._udp.getsockname()

    async def _recv(self):
        msg, other = await self._udp.recvfrom(BUFFER_SIZE)
        if msg[:4] != Broadcaster.MAGIC:
            raise ValueError('Invalid broadcast magic.')
        msg = Message.from_bytes(msg[4:])
        return msg, other

    async def send(self, type, data):
        """Send a message on the multicast network."""
        msg = Message(self._uuid, type, data)
        msg = Broadcaster.MAGIC + msg.encode()
        return await self._udp.sendto(msg, self._address)

    def stop(self):
        """Stops multicaster."""
        super().stop()
        self._udp.close()
