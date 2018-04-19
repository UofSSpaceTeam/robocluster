import asyncio
import socket
import struct
import json
import os

from robocluster.net import AsyncSocket
from robocluster.loop import Looper
from util import as_coroutine


async def amain(name, other, loop):
    from contextlib import suppress
    from time import time

    member = Member(name, 12345)
    member.start()

    def echo(*args, **kwargs):
        print(args, kwargs)
        return args, kwargs

    def echo_send(*args, **kwargs):
        print('echo_send', args, kwargs)

    def echo_sub(*args, **kwargs):
        print('echo_sub', args, kwargs)

    member.on_recv('send', echo_send)
    member.subscribe(other, 'pub', echo_sub)
    member.on_request('thing', echo)

    while ...:
        await member.sleep(1)
        with suppress(UnknownPeer):
            await member.send(other, 'send', time())
            result = await member.request(other, 'thing', 1, 2, 3, a=1, b=2)
            print('result:', result)
        await member.publish('pub', time())


def main():
    import asyncio
    import sys
    from loop import LoopThread
    loop = LoopThread()
    loop.start()
    loop.create_task(amain(sys.argv[1], sys.argv[2], loop.loop))
    try:
        loop.join()
    except KeyboardInterrupt:
        loop.stop()


class Error(Exception):
    pass


class UnknownPeer(Error):
    pass


class Member(Looper):
    def __init__(self, name, port, key=None, loop=None):
        super().__init__(loop)
        self.name = name
        self.uid = int.from_bytes(os.urandom(4), 'big')
        self.wanted = set()

        self.subscriptions = set()

        self._send_endpoints = {}
        self._request_endpoints = {}

        self._peers = {}
        self._accepter = _Accepter(self)
        self._gossiper = _Gossiper(self, port, key=key)

    def try_peer(self, peer):
        try:
            return self._peers[peer]
        except KeyError:
            raise UnknownPeer(peer)

    def on_recv(self, endpoint, callback):
        self._send_endpoints[endpoint] = as_coroutine(callback)

    def subscribe(self, peer, endpoint, callback):
        endpoint = '{}/{}'.format(peer, endpoint)
        self.on_recv(endpoint, callback)
        self.subscriptions.add(endpoint)

    async def send(self, peer, endpoint, data):
        await self.try_peer(peer).send(endpoint, data)

    async def publish(self, endpoint, data):
        endpoint = '{}/{}'.format(self.name, endpoint)
        for peer in self._peers.values():
            await peer.publish(endpoint, data)

    async def _handle_send(self, endpoint, data):
        try:
            endpoint = self._send_endpoints[endpoint]
        except KeyError:
            return
        await endpoint(data)

    def on_request(self, endpoint, callback):
        self._request_endpoints[endpoint] = as_coroutine(callback)

    async def request(self, peer, endpoint, *args, **kwargs):
        return await self.try_peer(peer).request(endpoint, *args, **kwargs)

    async def _handle_request(self, endpoint, *args, **kwargs):
        try:
            endpoint = self._request_endpoints[endpoint]
        except KeyError:
            return 'no such endpoint'
        result = await endpoint(*args, **kwargs)
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
        super().__init__(member.loop)
        self.member = member

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
    def __init__(self, member, name, uid):
        super().__init__(member)

        self.name = name
        self.uid = uid

        self._address = None
        self.subscriptions = set()

        self._wanted = set()
        self._is_wanted = asyncio.Event(loop=self.loop)

        self._pending = {}

        self._socket = None
        self._connected = asyncio.Event(loop=self.loop)

        self.add_daemon_task(self._recv_loop)

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
        self.member.wanted.add(self.name)
        return self._connected.wait()

    async def send(self, endpoint, data):
        # TODO: timeout?
        await self.connected
        packet = 'send', (endpoint, data)
        await self._send(packet)

    async def publish(self, endpoint, data):
        if endpoint in self.subscriptions:
            await self.send(endpoint, data)

    async def _handle_send(self, packet):
        endpoint, data = packet
        await self.member._handle_send(endpoint, data)

    async def request(self, endpoint, *args, **kwargs):
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
        await self._socket.send(size + packet)

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
                except (ConnectionRefusedError, OSError):
                    self.close()
                    await self.sleep(1)  # TODO: change delay?
                    continue

                await self._send(member.name)
                self._connected.set()

            size = await self._socket.recv(4)
            if not size:
                # Other side has been closed
                self.close()
                continue

            size = int.from_bytes(size, 'big')
            data = await self._socket.recv(size)

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

    @property
    def wanted(self):
        return self._wanted

    @wanted.setter
    def wanted(self, names):
        member = self.member
        self._wanted = names
        if self.name in member.wanted or member.name in self._wanted:
            self._is_wanted.set()
        else:
            self._is_wanted.clear()


class _Gossiper(_Component):
    def __init__(self, member, port, key=None):
        super().__init__(member)

        self._port = port

        if key is None:
            # create key from port
            self._key = (port*port).to_bytes(4, 'big')
        else:
            self._key = key

        self._socket = self.socket('udp', bind=('', self._port))
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        self.add_daemon_task(self._recv_loop)
        self.add_daemon_task(self._send_loop)

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
            peer.subscriptions = subscriptions
            peer.wanted = wanted
            peer.start()

    async def _send_loop(self):
        member = self.member
        address = '255.255.255.255', self._port
        while ...:
            data = (
                member.name,
                member.uid,
                member._accepter.port,
                tuple(member.wanted),
                tuple(member.subscriptions),
            )
            packet = json.dumps(data).encode()
            try:
                await self._socket.sendto(self._key + packet, address)
            except OSError as e:
                print(e)
            await self.sleep(1)


class _Accepter(_Component):
    def __init__(self, member):
        super().__init__(member)
        self._socket = self.socket('tcp', bind=('', 0))
        self._socket.listen()

        self.add_daemon_task(self._accept_loop)

    @property
    def port(self):
        return self._socket.getsockname()[1]

    async def _accept_loop(self):
        member = self.member
        while ...:
            conn, address = await self._socket.accept()
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
