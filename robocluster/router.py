import asyncio
import socket
import struct
import json
import ipaddress
from fnmatch import fnmatch
from uuid import uuid4

from .loop import Looper
from .net import AsyncSocket, key_to_multicast
from .util import as_coroutine


BUFFER_SIZE = 1024


def ip_info(addr):
    addr = ipaddress.ip_address(addr)
    if isinstance(addr, ipaddress.IPv6Address):
        return socket.AF_INET6, addr
    else:
        return socket.AF_INET, addr


class Message:
    def __init__(self, source, type, data):
        self.source = source
        self.type = type
        self.data = data

    @classmethod
    def from_bytes(cls, msg):
        try:
            packet = json.loads(msg.decode())
        except UnicodeDecodeError:
            raise ValueError('Invalid utf-8.')
        except json.JSONDecodeError:
            raise ValueError('Invalid JSON.')

        if any(k not in packet for k in ('source', 'type', 'data')):
            raise ValueError('Improperly formatted message.')

        return cls(packet['source'], packet['type'], packet['data'])

    def encode(self):
        return json.dumps({
            'source': self.source,
            'type': self.type,
            'data': self.data,
        }).encode()

    def __repr__(self):
        return '{}({!r}, {!r}, {!r})'.format(
            self.__class__.__name__,
            self.source,
            self.type,
            self.data
        )


class Multicaster(Looper):
    def __init__(self, group, port, loop=None):
        super().__init__(loop=loop)
        self._uuid = str(uuid4())
        self._callbacks = {}

        family, addr = ip_info(group)
        if not addr.is_multicast:
            raise ValueError('group is not multicast')

        self._group = str(addr), port

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

        self.add_daemon_task(self._recv)

    async def _recv(self):
        while True:
            msg, other = await self._udp_recv.recvfrom(BUFFER_SIZE)
            try:
                msg = Message.from_bytes(msg)
            except ValueError:
                continue

            if msg.source == self._uuid:
                continue

            try:
                callback = self._callbacks[msg.type]
            except KeyError:
                continue
            self.create_task(callback(other, msg))

    @property
    def address(self):
        return self._udp_recv.getsockname()

    async def cast(self, type, data):
        msg = Message(self._uuid, type, data)
        return await self._udp_send.sendto(msg.encode(), self._group)

    def on_cast(self, type, callback):
        self._callbacks[type] = as_coroutine(callback)

    def stop(self):
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


class Listener(Looper):
    def __init__(self, host, port, loop=None):
        super().__init__(loop=loop)
        self._callbacks = {}

        family, addr = ip_info(host)
        self._socket = AsyncSocket(family, socket.SOCK_STREAM)
        self._socket.bind((str(addr), port))
        self._socket.listen()

        self.add_daemon_task(self._listener)

    async def _listener(self):
        while True:
            conn, _ = await self._socket.accept()
            conn = Connection(conn)
            self.create_task(self._handle_connection(conn))

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

    @property
    def address(self):
        return self._socket.getsockname()

    def on_connect(self, type, callback):
        self._callbacks[type] = as_coroutine(callback)

    def stop(self):
        super().stop()
        self._socket.close()


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


class Router(Looper):
    def __init__(self, name, group, ip_family='ipv6', loop=None):
        super().__init__(loop=loop)

        self.name = name
        self.group = group
        self._peers = {}

        group, port = key_to_multicast(group, family=ip_family)
        self._caster = Multicaster(group, port, loop=loop)

        listen = '::' if ip_family else '0.0.0.0'
        self._listener = Listener(listen, 0, loop=loop)

        self._caster.on_cast('heartbeat', self._heartbeat_callback)
        self.add_daemon_task(self._heartbeat_daemon)
        self.add_daemon_task(self._heartbeat_debug)

        self._subscriptions = []
        self._caster.on_cast('publish', self._publish_callback)

    async def publish(self, topic, data):
        return await self._caster.cast('publish', {
            'topic': '{}/{}'.format(self.name, topic),
            'data': data
        })

    async def _publish_callback(self, other, msg):
        topic = msg.data['topic']
        data = msg.data['data']
        for key, coro in self._subscriptions:
            if fnmatch(topic, key):
                self._loop.create_task(coro(topic, data))

    def subscribe(self, topic, callback):
        coro = as_coroutine(callback)
        self._subscriptions.append((topic, coro))

    async def connect(self, route):
        pass

    def on_connect(self, route, callback):
        pass

    HEARTBEAT_RATE = 0.1
    HEARTBEAT_EXPIRE = 1

    async def _heartbeat_debug(self):
        while True:
            info = [
                (name, peer['listen'])
                for name, peer in self._peers.items()
            ]
            print(info)
            await self.sleep(0.5)

    async def _heartbeat_daemon(self):
        while True:
            await self._caster.cast('heartbeat', {
                'source': self.name,
                'listen': self._listener.address[1],
            })
            await self.sleep(self.HEARTBEAT_RATE)

    async def _heartbeat_callback(self, other, msg):
        source = msg.data['source']
        listen = msg.data['listen']
        try:
            peer = self._peers[source]
            peer['expire'].cancel()
        except KeyError:
            self._peers[source] = peer = {}
        peer['listen'] = other[0], listen
        peer['expire'] = self.create_task(self._heartbeat_expire(source))

    async def _heartbeat_expire(self, name):
        await self.sleep(self.HEARTBEAT_EXPIRE)
        if name in self._peers:
            del self._peers[name]

    def start(self):
        super().start()
        self._caster.start()
        self._listener.start()

    def stop(self):
        super().stop()
        self._caster.stop()
        self._listener.stop()
