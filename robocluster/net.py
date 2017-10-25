import asyncio
import json
import socket
import struct
import ipaddress
from hashlib import sha256


class Socket:
    """Datagram socket wrapper with encoded transport."""

    def __init__(self, address, transport='json', loop=None):
        """
        Initialize a socket.

        Args:
            address (str): Address in form 'host:port'
            transport (str, optional): Transport type to use.
                Supported values: 'raw', 'utf-8', 'json', and 'msgpack'
                Defaults to 'json'.
            loop (optional): Event loop to use.
                Defaults to current event loop.
        """
        host, port = address.split(':')
        port = int(port)
        if port < 1 or port > 65535:
            raise ValueError('invalid port number')

        self._loop = loop if loop else asyncio.get_event_loop()

        self._address = (host, port)
        self._transport = transport
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._bound = False

    @property
    def buffer_size(self):
        """Return buffer size of socket."""
        return self._socket.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)

    @property
    def is_multicast(self):
        """Return True if the socket is on a multicast group."""
        try:
            ip_address = ipaddress.IPv4Address(self._address[0])
            return ip_address.is_multicast
        except ipaddress.AddressValueError:
            return False

    def bind(self):
        """Bind to the socket."""
        if self.is_multicast:
            mreq = struct.pack(
                '4sl',
                socket.inet_aton(self._address[0]),
                socket.htonl(socket.INADDR_ANY)
            )
            self._socket.setsockopt(
                socket.IPPROTO_IP,
                socket.IP_ADD_MEMBERSHIP,
                mreq
            )
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(self._address)
        self._bound = True

    def send(self, data, address=None):
        """Send a packet to the network."""
        if self._bound and self.is_multicast:
            raise RuntimeError('cannot send on bound multicast socket')

        future = self._loop.create_future()
        fileno = self._socket.fileno()

        data = self.encode(data)
        address = address if address else self._address

        def _writer():
            self._loop.remove_writer(fileno)
            try:
                n_bytes = self._socket.sendto(data, address)
            except (BlockingIOError, InterruptedError):
                self._loop.add_writer(fileno, _writer)
            else:
                future.set_result(n_bytes)

        self._loop.add_writer(fileno, _writer)
        return future

    def receive(self):
        """Recieve a packet from the network."""
        future = self._loop.create_future()
        fileno = self._socket.fileno()

        def _reader():
            self._loop.remove_reader(fileno)
            try:
                data, address = self._socket.recvfrom(self.buffer_size)
            except (BlockingIOError, InterruptedError):
                self._loop.add_reader(fileno, _reader)
            else:
                data = self.decode(data)
                future.set_result((data, address))

        self._loop.add_reader(fileno, _reader)
        return future

    def close(self):
        """Close the socket."""
        if self._multicast:
            mreq = struct.pack(
                '4sl',
                socket.inet_aton(self._address[0]),
                socket.htonl(socket.INADDR_ANY)
            )
            self._socket.setsockopt(
                socket.IPPROTO_IP,
                socket.IP_DROP_MEMBERSHIP,
                mreq
            )

        self._socket.close()

    def encode(self, data):
        """Encode data for network."""
        if self._transport == 'raw':
            return data

        if self._transport == 'utf-8':
            return data.encode()

        if self._transport == 'json':
            return json.dumps(data).encode()

        if self._transport == 'msgpack':
            try:
                import msgpack
                return msgpack.packb(data)
            except ImportError:
                pass

        raise RuntimeError('transport type not supported')

    def decode(self, data):
        """Decode data from network."""
        if self._transport == 'raw':
            return data

        if self._transport == 'utf-8':
            return data.decode()

        if self._transport == 'json':
            return json.loads(data.decode())

        if self._transport == 'msgpack':
            try:
                import msgpack
                return msgpack.unpackb(data, encoding='utf-8')
            except ImportError:
                pass

        raise RuntimeError('transport type not supported')


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
    return '224.0.0.{}:{}'.format(group, port)
