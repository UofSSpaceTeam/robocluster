import asyncio
import socket as socket_m
from functools import partial, wraps
from hashlib import sha256


__all__ = [
    'AsyncSocket',
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
