import asyncio
import socket
import json
import os
import logging
from fnmatch import fnmatch
from ipaddress import IPv4Network

from .net import AsyncSocket
from .looper import Looper
from .util import as_coroutine


log = logging.getLogger(__name__)


class Error(Exception):
    pass


class UnknownPeer(Error):
    pass


class Member(Looper):
    def __init__(self, name, network, port, key=None, loop=None):
        super().__init__(loop)
        self.name = name
        self.uid = int.from_bytes(os.urandom(4), 'big')
        self._wanted = set()

        self._subscriptions = set()

        self._send_endpoints = {}
        self._request_endpoints = {}

        self._peers = {}
        self._accepter = _Accepter(self)
        self._gossiper = _Gossiper(self, network, port, key=key)

    def is_wanted(self, name):
        for want in self._wanted:
            if fnmatch(name, want):
                return True
        return False

    async def try_peer(self, peer):
        for _ in range(5):
            try:
                return self._peers[peer]
            except KeyError:
                await self.sleep(self._gossiper.GOSSIP_RATE)
        raise UnknownPeer(peer)

    def on_recv(self, endpoint, callback):
        self._send_endpoints[endpoint] = as_coroutine(callback)

    def subscribe(self, peer, endpoint, callback):
        endpoint = '{}/{}'.format(peer, endpoint)
        self._wanted.add(peer)
        self.on_recv(endpoint, callback)
        self._subscriptions.add(endpoint)

    async def send(self, peer, endpoint, data):
        peer = await self.try_peer(peer)
        await peer.send(endpoint, data)

    async def publish(self, endpoint, data):
        endpoint = '{}/{}'.format(self.name, endpoint)
        for peer in self._peers.values():
            await peer.publish(endpoint, data)

    async def _handle_send(self, source, endpoint, data):
        for end, callback in self._send_endpoints.items():
            if fnmatch(endpoint, end):
                if end in self._subscriptions:
                    await callback(endpoint, data)
                else:
                    await callback(source, data)

    def on_request(self, endpoint, callback):
        self._request_endpoints[endpoint] = as_coroutine(callback)

    async def request(self, peer, endpoint, *args, **kwargs):
        peer = await self.try_peer(peer)
        return await peer.request(endpoint, *args, **kwargs)

    async def _handle_request(self, endpoint, *args, **kwargs):
        try:
            callback = self._request_endpoints[endpoint]
        except KeyError:
            return 'no such endpoint'
        result = await callback(*args, **kwargs)
        return result

    def start(self):
        super().start()
        self._accepter.start()
        self._gossiper.start()

    def stop(self):
        super().stop()
        self._accepter.stop()
        self._gossiper.stop()
        for peer in self._peers.values():
            peer.stop()


class _Component(Looper):
    def __init__(self, member):
        self.member = member
        super().__init__(self.member.loop)

    def socket(self, kind, bind=None):
        try:
            kind = {
                'tcp': socket.SOCK_STREAM,
                'udp': socket.SOCK_DGRAM,
            }[kind]
        except KeyError:
            raise ValueError

        s = AsyncSocket(socket.AF_INET, kind, loop=self.loop)
        if bind is not None:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, 'SO_REUSEPORT'):
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            s.bind(bind)
        return s


class _Peer(_Component):
    CONNECTION_RETRY_RATE = 0.1

    def __init__(self, member, name, uid):
        super().__init__(member)

        self.name = name
        self.uid = uid

        self._address = None
        self._subscriptions = set()

        self._wanted = set()
        self._is_wanted = asyncio.Event(loop=self.loop)

        self._pending = {}

        self._socket = None
        self._connected = asyncio.Event(loop=self.loop)

        self.create_daemon(self._recv_loop)

    @property
    def address(self):
        return self._address

    @address.setter
    def address(self, new):
        if new != self._address:
            self.close()
            self._address = new

    @property
    def connected(self):
        return self._connected.wait()

    async def send(self, endpoint, data, register=True):
        # TODO: timeout?
        self.member._wanted.add(self.name)
        await self.connected
        packet = 'send', (endpoint, data)
        await self._send(packet)

    async def publish(self, endpoint, data):
        for subscription in self._subscriptions:
            if fnmatch(endpoint, subscription):
                # peer should already be wanted from the other end
                await self.connected
                packet = 'send', (endpoint, data)
                await self._send(packet)

    async def _handle_send(self, packet):
        endpoint, data = packet
        await self.member._handle_send(self.name, endpoint, data)

    async def request(self, endpoint, *args, **kwargs):
        self.member._wanted.add(self.name)
        await self.connected
        rid = int.from_bytes(os.urandom(4), 'big')
        packet = 'request', (rid, endpoint, args, kwargs)
        future = self._pending[rid] = asyncio.Future(loop=self.loop)
        await self._send(packet)
        return await future

    async def _handle_request(self, packet):
        rid, endpoint, args, kwargs = packet
        result = await self.member._handle_request(endpoint, *args, **kwargs)
        packet = 'response', (rid, result)
        await self._send(packet)

    async def _handle_response(self, packet):
        rid, result = packet
        future = self._pending.pop(rid, None)
        if future:
            future.set_result(result)

    async def accept(self, conn):
        if self._socket is not None:
            conn.close()
        self._socket = conn
        self._connected.set()

    async def _send(self, packet):
        packet = json.dumps(packet).encode()
        size = len(packet).to_bytes(4, 'big')
        try:
            return await self._socket.send(size + packet)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.exception(e)
            self.close()
            return 0

    async def _recv(self, size):
        try:
            data = await self._socket.recv(size)
            if not data:
                self.close()
            return data
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.exception(e)
            self.close()

    async def _recv_loop(self):
        member = self.member

        while ...:
            await self._is_wanted.wait()

            if member.uid >= self.uid:
                # The other side will connect to me
                await self._connected.wait()
            elif not self._connected.is_set():
                # I am responsible for doing the connect!
                self._socket = self.socket('tcp')

                try:
                    await self._socket.connect(self._address)
                except (ConnectionResetError, ConnectionRefusedError, OSError):
                    self.close()
                    await self.sleep(self.CONNECTION_RETRY_RATE)
                    continue

                await self._send(member.name)
                self._connected.set()

            size = await self._recv(4)
            if not size:
                # Other side has been closed
                continue

            size = int.from_bytes(size, 'big')
            data = await self._recv(size)

            try:
                data = json.loads(data.decode())
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue

            try:
                kind, packet = data
            except ValueError:
                continue

            handler = getattr(self, '_handle_' + kind, None)
            if handler:
                await handler(packet)

    def close(self):
        if self._socket is not None:
            self._connected.clear()
            self._socket.close()
            self._socket = None

    def is_wanted(self, name):
        for want in self._wanted:
            if fnmatch(name, want):
                return True
        return False

    @property
    def wanted(self):
        return self._wanted

    @wanted.setter
    def wanted(self, names):
        member = self.member
        self._wanted = names
        if member.is_wanted(self.name) or self.is_wanted(member.name):
            self._is_wanted.set()
        else:
            self._is_wanted.clear()


class _Gossiper(_Component):
    GOSSIP_RATE = 0.1

    def __init__(self, member, network, port, key=None):
        super().__init__(member)

        network = IPv4Network(network, strict=False)
        self._address = str(network.broadcast_address), port

        if key is None:
            # create key from port
            self._key = (port*port).to_bytes(4, 'big')
        else:
            self._key = key

        self._socket = self.socket('udp', bind=('', self._address[1]))
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        self.create_daemon(self._recv_loop)
        self.create_daemon(self._send_loop)

    async def _recv_loop(self):
        member = self.member
        while ...:
            packet, source = await self._socket.recvfrom(1024)

            klen = len(self._key)
            if len(packet) < klen:
                continue
            key, packet = packet[:klen], packet[klen:]
            if key != self._key:
                continue

            try:
                data = json.loads(packet.decode())
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue

            try:
                name, uid, port, wanted, subscriptions = data
                address = source[0], port
                subscriptions = set(subscriptions)
                wanted = set(wanted)
            except (TypeError, ValueError):
                continue

            if uid == member.uid:
                continue

            try:
                peer = member._peers[name]
            except KeyError:
                peer = member._peers[name] = _Peer(member, name, uid)

            peer.address = address
            peer._subscriptions = subscriptions
            peer.wanted = wanted
            peer.start()

    async def _send_loop(self):
        member = self.member
        while ...:
            data = (
                member.name,
                member.uid,
                member._accepter.port,
                tuple(member._wanted),
                tuple(member._subscriptions),
            )
            packet = self._key + json.dumps(data).encode()
            try:
                await self._socket.sendto(packet, self._address)
            except OSError as e:
                log.exception(e)
            await self.sleep(self.GOSSIP_RATE)


class _Accepter(_Component):
    def __init__(self, member):
        super().__init__(member)
        self._socket = self.socket('tcp', bind=('', 0))
        self._socket.listen()

        self.create_daemon(self._accept_loop)

    @property
    def port(self):
        return self._socket.getsockname()[1]

    async def _accept_loop(self):
        member = self.member
        while ...:
            conn, _ = await self._socket.accept()
            size = await conn.recv(4)
            size = int.from_bytes(size, 'big')
            name = await conn.recv(size)

            try:
                name = json.loads(name.decode())
                peer = member._peers[name]
            except (UnicodeDecodeError, KeyError, json.JSONDecodeError):
                conn.close()
                continue

            await peer.accept(conn)


if __name__ == '__main__':
    exit(main())
