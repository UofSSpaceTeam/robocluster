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
HEARTBEAT_DEBUG = False


def ip_info(addr):
    """Verify and detecet ip address family."""
    addr = ipaddress.ip_address(addr)
    if isinstance(addr, ipaddress.IPv6Address):
        return socket.AF_INET6, addr
    else:
        return socket.AF_INET, addr


class Message:
    """Base message type for network."""

    def __init__(self, source, type, data):
        """
        Initialize a message.

        Arguments:
            source: source of message (str)
            type: message type (str)
            data: JSON encodable data.
        """
        self.source = source
        self.type = type
        self.data = data

    @classmethod
    def from_bytes(cls, msg):
        """Create a Message from bytes."""
        try:
            return cls.from_string(msg.decode())
        except UnicodeDecodeError:
            raise ValueError('Invalid utf-8.')

    @classmethod
    def from_string(cls, msg):
        """Create a Message from a utf-8 string."""
        try:
            packet = json.loads(msg)
        except json.JSONDecodeError:
            raise ValueError('Invalid JSON.')

        if any(k not in packet for k in ('source', 'type', 'data')):
            raise ValueError('Improperly formatted message.')

        return cls(packet['source'], packet['type'], packet['data'])

    def encode(self):
        """Encode the message to bytes."""
        return self.to_json().encode()

    def to_json(self):
        return json.dumps({
            'source': self.source,
            'type': self.type,
            'data': self.data,
        })

    def __repr__(self):
        return '{}({!r}, {!r}, {!r})'.format(
            self.__class__.__name__,
            self.source,
            self.type,
            self.data
        )


class Multicaster(Looper):
    def __init__(self, group, port, loop=None):
        """
        Initialize the multicaster.

        Arguments:
            group: multicast group to send and receive from.
            port: port to bind to.

        Optional Arguments:
            loop: event loop to use.
        """
        super().__init__(loop=loop)
        self._uuid = str(uuid4())
        self._callbacks = {}

        family, addr = ip_info(group)
        if not addr.is_multicast:
            raise ValueError('group is not multicast')

        self._group = str(addr), port

        sock = AsyncSocket(family, socket.SOCK_DGRAM, loop=loop)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
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
        """Receive daemon task."""
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
        """Address of the receiving socket."""
        return self._udp_recv.getsockname()

    async def cast(self, type, data):
        """Send a message on the multicast network."""
        msg = Message(self._uuid, type, data)
        return await self._udp_send.sendto(msg.encode(), self._group)

    def on_cast(self, type, callback):
        """Add a callback to a message type."""
        self._callbacks[type] = as_coroutine(callback)

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


class Listener(Looper):
    """Listens for new connections."""

    def __init__(self, host, port, loop=None):
        """
        Initialize the listener.

        Arguments:
            host: host ip to bind to
            port: port number to bind to

        Optional Arguments:
            loop: event loop to use.
        """
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
    """Connection wrapper for bare AsyncSocket."""

    def __init__(self, sock):
        """Initialize the connection from a bare socket."""
        self._socket = sock

    @classmethod
    async def from_addr(cls, host, port):
        """Connect to a listening server by host and port."""
        family, host = ip_info(host)
        print(host)
        sock = AsyncSocket(family, socket.SOCK_STREAM)
        await sock.connect((str(host), port))
        return cls(sock)

    async def write(self, msg):
        """Write a message to the connection."""
        return await self._socket.send(msg.encode())

    async def read(self):
        """Read a message from the connection."""
        return Message.from_bytes(await self._socket.recv(BUFFER_SIZE))

    def close(self):
        """Close the connection."""
        self._socket.close()


class Router(Looper):
    def __init__(self, name, group, ip_family='ipv6', loop=None):
        """
        Initialize the router.

        Arguments:
            name: name of the router, will be sent to peers (str)
            group: name of multicast group for peers (str)

        Optional Arguments:
            ip_family: either ipv4 or ipv6
            loop: event loop that the router runs on.
        """
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
        if HEARTBEAT_DEBUG:
            self.add_daemon_task(self._heartbeat_debug)

        self._subscriptions = []
        self._caster.on_cast('publish', self._publish_callback)
        self.message_callbacks = []

    async def publish(self, topic, data):
        """Publish a message to a topic."""
        return await self._caster.cast('publish', {
            'topic': '{}/{}'.format(self.name, topic),
            'data': data
        })

    async def _publish_callback(self, other, msg):
        """Handle published messages and start tasks for each callback."""
        topic = msg.data['topic']
        data = msg.data['data']
        for key, coro in self._subscriptions:
            if fnmatch(topic, key):
                self._loop.create_task(coro(topic, data))
        for callback in self.message_callbacks:
            await callback(msg)

    def on_message(self, callback):
        """Add a handler to be called when the router receives a message."""
        self.message_callbacks.append(as_coroutine(callback))

    async def route_message(self, msg):
        """Figure out what to do with an arbitrary message."""
        if msg.type == 'publish':
            await self.publish(msg.data['topic'], msg.data['data'])
        elif msg.type == 'send':
            pass
        elif msg.type == 'request':
            pass
        elif msg.type == 'heartbeat':
            pass

    def subscribe(self, topic, callback):
        """Subscribe to a topic."""
        coro = as_coroutine(callback)
        self._subscriptions.append((topic, coro))

    async def connect(self, name, route):
        """Connect to a peer by name with specific route."""
        # TODO: do we wait until the peer is connected?
        if name not in self._peers:
            raise RuntimeError('peer not available')
        conn = await Connection.from_addr(*self._peers[name]['listen'])
        await conn.write(Message(self.name, 'connect', {'route': route}))
        return conn

    def on_connect(self, route, callback):
        """Register a callback for a route."""
        coro = as_coroutine(callback)
        self._routes.append((route, coro))

    async def _connect_callback(self, conn, route):
        """Handle new connection."""
        print(conn, route)
        conn.close()

    HEARTBEAT_RATE = 0.1
    HEARTBEAT_EXPIRE = 1

    async def _heartbeat_debug(self):
        """Debug task for heartbeats."""
        while True:
            info = [
                (name, peer['listen'])
                for name, peer in self._peers.items()
            ]
            print(info)
            await self.sleep(0.5)

    async def _heartbeat_daemon(self):
        """Daemon task for heartbeat sending."""
        while True:
            await self._caster.cast('heartbeat', {
                'source': self.name,
                'listen': self._listener.address[1],
            })
            await self.sleep(self.HEARTBEAT_RATE)

    async def _heartbeat_callback(self, other, msg):
        """Handle heartbeat when received."""
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
        """Expire the peer in a bit."""
        await self.sleep(self.HEARTBEAT_EXPIRE)
        if name in self._peers:
            del self._peers[name]

    def start(self):
        """Start the router."""
        super().start()
        self._caster.start()
        self._listener.start()

    def stop(self):
        """Stop the router."""
        super().stop()
        self._caster.stop()
        self._listener.stop()
