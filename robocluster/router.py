import asyncio
import socket
import struct
import json
from uuid import uuid4

from .loop import LoopedTask
from .net import AsyncSocket
from .util import as_coroutine


BUFFER_SIZE = 1024


class Message:
    def __init__(self, source, kind, data):
        self.source = source
        self.kind = kind
        self.data = data

    @classmethod
    def from_bytes(cls, msg):
        try:
            packet = json.loads(msg.decode())
        except UnicodeDecodeError:
            raise ValueError('Invalid utf-8.')
        except json.JSONDecodeError:
            raise ValueError('Invalid JSON.')

        if any(k not in packet for k in ('source', 'kind', 'data')):
            raise ValueError('Improperly formatted message.')

        return cls(packet['source'], packet['kind'], packet['data'])

    def encode(self):
        return json.dumps({
            'source': self.source,
            'kind': self.kind,
            'data': self.data,
        }).encode()

    def __repr__(self):
        return '{}({!r}, {!r}, {!r})'.format(
            self.__class__.__name__,
            self.source,
            self.kind,
            self.data
        )


class Multicaster(LoopedTask):
    def __init__(self, group, port, loop=None):
        super().__init__(loop=loop)
        self._uuid = str(uuid4())
        self._callbacks = {}

        info, *_ = socket.getaddrinfo(group, port)  # blocking call

        self._group = info[4]
        family = info[0]

        sock = AsyncSocket(family, socket.SOCK_DGRAM, loop=loop)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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

    @property
    def address(self):
        return self._udp_recv.getsockname()

    async def cast(self, kind, data):
        msg = Message(self._uuid, kind, data)
        return await self._udp_send.sendto(msg.encode(), self._group)

    def on_cast(self, kind, callback):
        self._callbacks[kind] = as_coroutine(callback)

    async def _looped_task(self):
        while True:
            msg, other = await self._udp_recv.recvfrom(BUFFER_SIZE)
            try:
                msg = Message.from_bytes(msg)
            except ValueError:
                continue

            if msg.source == self._uuid:
                continue

            try:
                callback = self._callbacks[msg.kind]
            except KeyError:
                continue
            self._loop.create_task(callback(other, msg))

    def stop(self):
        if not super().stop():
            return False

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
        return True


class Listener(LoopedTask):
    def __init__(self, host, port, loop=None):
        super().__init__(loop=loop)
        self._uuid = str(uuid4())
        self._callbacks = {}

        info, *_ = socket.getaddrinfo(host, port)  # blocking call
        family = info[0]
        address = info[4]
        self._socket = AsyncSocket(family, socket.SOCK_STREAM)
        self._socket.bind(address)
        self._socket.listen()

    @property
    def address(self):
        return self._socket.getsockname()

    def on_connect(self, kind, callback):
        self._callbacks[kind] = as_coroutine(callback)

    async def _looped_task(self):
        while True:
            conn, _ = await self._socket.accept()
            conn = Connection(conn)
            self._loop.create_task(self._handle_connection(conn))

    async def _handle_connection(self, conn):
        while True:
            try:
                msg = await conn.read()
                # TODO: figure out which callback is needed
                print(msg)
            except Exception as e:
                print(e)
                break
        conn.close()

    def stop(self):
        if not super().stop():
            return False
        self._socket.close()
        return True


class Connection:
    def __init__(self, sock):
        self._socket = sock

    @classmethod
    async def from_addr(cls, host, port):
        """We want to be able to create a connection from the client side."""
        info, *_ = socket.getaddrinfo(group, port)  # blocking call
        sock = AsyncSocket(info[0], socket.SOCK_STREAM)
        await sock.connect(info[4])
        return cls(sock)

    async def write(self, data):
        msg = Message('source', 'type', data).encode()
        return await self._socket.send(msg)

    async def read(self):
        return Message.from_bytes(await self._socket.recv(BUFFER_SIZE))

    def close(self):
        self._socket.close()


class Router:
    HEARTBEAT_RATE = 0.1

    def __init__(self, group, port):
        self._caster = Multicaster(group, port)
        self._listener = Listener('', 0)  # TODO: match IPv# of caster

    async def publish(self, topic, data):
        return await self._caster.cast('pubish', {
            'topic': topic,
            'data': data
        })

    async def subscribe(self, topic, callback):
        pass

    async def connect(self, route):
        pass

    def on_connect(self, route, callback):
        pass

    async def _task_heartbeat(self):
        while True:
            await self._caster.cast('heartbeat', {
                'source': None,
                'listen': self._listener.address[1],
            })
            await asyncio.sleep(self.HEARTBEAT_RATE, loop=self._loop)

    def start(self):
        self._loop.create_task(self._task_heartbeat())
