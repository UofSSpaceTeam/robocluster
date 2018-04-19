import asyncio
import socket
import struct
import json
import os

from robocluster.net import AsyncSocket
from robocluster.loop import Looper


async def amain(name, other, loop):
    member = Member(name, b'deafbeef', 12345)
    member.start()
    member.wanted.append(other)
    while ...:
        await member.sleep(1)
        await member.send(other, 'hello', 'hello from: ' + name)


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


class Member(Looper):
    def __init__(self, name, gossip_key, gossip_port, loop=None):
        super().__init__(loop)
        self.name = name
        self.uid = int.from_bytes(os.urandom(4), 'big')
        self.wanted = []

        self._peers = {}
        self._connector = _Connector(self)
        self._gossiper = _Gossiper(self, gossip_port, gossip_key)

    def start(self):
        super().start()
        self._connector.start()
        self._gossiper.start()

    def stop(self):
        super().stop()
        self._connector.stop()
        self._gossiper.stop()
        for peer in self._peers.values():
            peer.stop()

    async def _want_peer(self, peer):
        if peer not in self.wanted:
            self.wanted.append(peer)
        while ...:
            try:
                return self._peers[peer]
            except KeyError:
                # TODO: handling a peer that never appears?
                await self.sleep(0.5)

    async def send(self, peer, event, data):
        peer = await self._want_peer(peer)
        packet = {
            'event': ('snd', event),
            'data': data,
        }
        s =  await peer.send(packet)

    async def request(self, peer, endpoint, *args, **kwargs):
        peer = await self._want_peer(peer)
        pid = os.random(4)
        self._requests
        packet = {
            'event': ('req', endpoint),
            'data': {
                'args': args,
                'kwargs': kwargs
            }
        }

    async def _handle(self, peer, event, data):
        print(peer, event, data)

    async def handle(self, event, callback):
        pass

    async def unhandle(self, event, callback, count=1):
        pass


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
        self._wanted = []
        self._socket = None
        self._ready = asyncio.Event(loop=self.loop)

        self.add_daemon_task(self._recv_loop)

    @property
    def address(self):
        return self._address

    @address.setter
    def address(self, new):
        if new != self._address:
            self.close()
            self._address = new

    async def connect(self):
        member = self.member

        if self._socket is not None:
            return self._socket

        if member.uid >= self.uid:
            raise RuntimeError('Should not be connecting to lesser id')

        sock = self._socket = self.socket('tcp')

        try:
            await sock.connect(self._address)
        except ConnectionRefusedError:
            return

        await sock.send(member.name.encode())
        self._ready.set()

    async def accept(self, conn):
        if self._socket is not None:
            conn.close()
        self._socket = conn
        self._ready.set()

    async def send(self, data):
        await self._ready.wait()
        packet = json.dumps(data).encode()
        return await self._socket.send(packet)

    async def _recv_loop(self):
        member = self.member

        while ...:
            await self._ready.wait()
            packet = await self._socket.recv(1024)
            if not packet:
                self.close()
                continue

            try:
                packet = json.loads(packet.decode())
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue

            try:
                event = packet['event']
                data = packet['data']
            except KeyError:
                continue

            await member._handle(self.name, event, data)

    def close(self):
        if self._socket is not None:
            self._ready.clear()
            self._socket.close()
            self._socket = None


class _Gossiper(_Component):
    def __init__(self, member, port, key):
        super().__init__(member)
        self._socket = self.socket('udp', bind=('', port))
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        self._key = key
        self._port = port

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
                name = data['name']
                uid = data['uid']
                wanted = data['wanted']
                address = source[0], data['port']
            except KeyError:
                continue

            if uid == member.uid:
                continue

            try:
                peer = member._peers[name]
            except KeyError:
                peer = member._peers[name] = _Peer(member, name, uid)

            peer.address = address
            peer.wanted = wanted
            peer.start()

    async def _send_loop(self):
        member = self.member
        address = '255.255.255.255', self._port
        while ...:
            data = {
                'uid': member.uid,
                'name': member.name,
                'port': member._connector.port,
                'wanted': member.wanted,
            }
            packet = json.dumps(data).encode()
            try:
                await self._socket.sendto(self._key + packet, address)
            except OSError as e:
                print(e)
            await self.sleep(1)


class _Connector(_Component):
    def __init__(self, member):
        super().__init__(member)
        self._socket = self.socket('tcp', bind=('', 0))
        self._socket.listen()

        self.add_daemon_task(self._conncect_loop)
        self.add_daemon_task(self._listen_loop)

    @property
    def port(self):
        return self._socket.getsockname()[1]

    async def _listen_loop(self):
        member = self.member
        while ...:
            conn, address = await self._socket.accept()
            name = await conn.recv(1024)

            try:
                name = name.decode()
                peer = member._peers[name]
            except (UnicodeDecodeError, KeyError):
                conn.close()
                continue

            await peer.accept(conn)

    async def _conncect_loop(self):
        member = self.member
        while ...:
            for name, peer in member._peers.items():
                if member.name in peer.wanted or name in member.wanted:
                    if member.uid < peer.uid:
                        await peer.connect()
            await self.sleep(1)

if __name__ == '__main__':
    exit(main())
