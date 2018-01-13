import asyncio
import json
import socket as socket_m
from functools import partial, wraps
from hashlib import sha256


__all__ = [
    'AsyncSocket',
    'MulticastSender',
    'MulticastReceiver',
    'MulticastTranceiver',
    'key_to_multicast',
]


class AsyncSocket:
    """Socket wrapper for asyncio."""

    def __init__(self, *args, socket=None, loop=None, **kwargs):
        self._loop = loop if loop else asyncio.get_event_loop()
        self._socket = socket if socket else socket_m.socket(*args, **kwargs)
        # TODO: ensure this never changes, async sockets cannot be blocking
        self.setblocking(False)

    @classmethod
    def from_socket(cls, socket, loop=None):
        """Create an AsyncSocket from a normal socket."""
        return cls(socket=socket, loop=loop)

    @wraps(socket_m.socket.accept)
    async def accept(self):
        conn, addr = await self._loop.sock_accept(self._socket)
        return self.__class__.from_socket(conn, loop=self._loop), addr

    @wraps(socket_m.socket.connect)
    async def connect(self, address):
        await self._loop.sock_connect(self._socket, address)

    @wraps(socket_m.socket.connect_ex)
    async def connect_ex(self, address):
        try:
            await self.connect(address)
            return 0
        except OSError as e:
            return e.errno

    @wraps(socket_m.socket.sendfile)
    async def sendfile(self, *args, **kwargs):
        # TODO: This method cannot be wrapped up the same way as the other
        #       send methods due to it's use of os.sendfile.
        raise NotImplementedError

    @wraps(socket_m.socket.dup)
    def dup(self):
        return self.__class__.from_socket(self._socket.dup(), loop=self._loop)

    def __getattr__(self, name):
        """
        Get an attribute by name.

        Wraps most of the blocking calls for sockets in a coroutine so
        they can be awaited.
        """
        attr = getattr(self._socket, name)
        loop = self._loop
        if name.startswith('send'):
            return self._wrap_io(attr, loop.add_writer, loop.remove_writer)
        elif name.startswith('recv'):
            return self._wrap_io(attr, loop.add_reader, loop.remove_reader)
        else:
            return attr

    def _wrap_io(self, func, adder, remover):
        fd = self.fileno()
        future = self._loop.create_future()
        @wraps(func)
        def wrapper(*args, **kwargs):
            remover(fd)
            if future.cancelled():
                return
            try:
                result = func(*args, **kwargs)
            except (BlockingIOError, InterruptedError):
                adder(fd, partial(wrapper, *args, **kwargs))
            except Exception as exc:
                future.set_exception(exc)
            else:
                future.set_result(result)
            return future
        return wrapper


class MulticastSender:
    def __init__(self, group, port, loop=None):
        self._group = group
        self._port = port

        self._socket = AsyncSocket(
            socket_m.AF_INET,
            socket_m.SOCK_DGRAM,
            loop=loop
        )

    async def send(self, packet):
        data = json.dumps(packet).encode()
        return await self._socket.sendto(data, (self._group, self._port))

    def close(self):
        self._socket.close()


class MulticastReceiver:
    def __init__(self, group, port, loop=None):
        self._group = group
        self._port = port

        self._socket = AsyncSocket(
            socket_m.AF_INET,
            socket_m.SOCK_DGRAM,
            loop=loop
        )
        self._socket.setsockopt(socket_m.SOL_SOCKET, socket_m.SO_REUSEADDR, 1)
        self._socket.setsockopt(socket_m.SOL_SOCKET, socket_m.SO_REUSEPORT, 1)
        self._socket.bind(('0.0.0.0', self._port))
        self._socket.setsockopt(socket_m.IPPROTO_IP, socket_m.IP_MULTICAST_TTL, 2)
        self._socket.setsockopt(socket_m.IPPROTO_IP, socket_m.IP_MULTICAST_LOOP, 1)
        self._socket.setsockopt(
            socket_m.IPPROTO_IP, socket_m.IP_ADD_MEMBERSHIP,
            socket_m.inet_aton(self._group) + socket_m.inet_aton('0.0.0.0')
        )

    async def receive(self):
        data, addr = await self._socket.recvfrom(1024)
        try:
            packet = json.loads(data.decode())
            return packet, addr
        except JSONDecodeError:
            return None, addr

    def close(self):
        self._socket.setsockopt(
            socket_m.IPPROTO_IP, socket_m.IP_DROP_MEMBERSHIP,
            socket_m.inet_aton(self._group) + socket_m.inet_aton('0.0.0.0')
        )
        self._socket.close()


class MulticastTranceiver:
    def __init__(self, group, port, loop=None):
        self._group = group
        self._port = port

        self._sender = MulticastSender(group, port, loop=loop)
        self._receiver = MulticastReceiver(group, port, loop=loop)

    async def send(self, data):
        return await self._sender.send(data)

    async def receive(self):
        return await self._receiver.receive()

    def close(self):
        self._sender.close()
        self._receiver.close()


def key_to_multicast(key):
    """Convert a key to a local multicast group."""
    digest = sha256(key.encode()).digest()

    # grab 1 byte for last octet of IP
    group = digest[0:1]
    # grab 2 bytes for port
    port = digest[1:3]

    group, port = map(
        lambda b: int.from_bytes(b, byteorder='little'),
        [group, port]
    )

    # mask bits 15 and 16 to make port ephemeral (49152-65535)
    port |= 0xC000

    # RFC 5771 states that IP multicast range of 224.0.0.0 to 224.0.0.255
    # are for use in local subnetworks.
    return '224.0.0.{}'.format(group), port
