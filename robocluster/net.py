"""Socket wrappers for robocluster."""

import json
import socket
import struct
from ipaddress import IPv4Address
from uuid import uuid4


def pack(unpacked):
    """Pack bytes for network."""
    return json.dumps(unpacked).encode()


def unpack(packed):
    """Unpack bytes from network."""
    return json.loads(packed.decode())


class Link:
    """
    A bidirectionaly link.

    Used for sending to other Links or MulticastReceivers.
    """

    def __init__(self, address, port):
        _ = IPv4Address(address)  # ensure ip address is valid
        if port < 1024 or port > 65535:
            raise ValueError('invalid port')

        self.address = (address, port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, data, to=None):
        """
        Send data to an address.

        Sends encoded data to the default address (self.address), if to is
        specified it will send to that address instead.
        """
        if to is None:
            to, pid = self.address, None
        else:
            to, pid = to
        return self.socket.sendto(self.encode(data, pid), to)

    def recieve(self):
        """Recieve data from the network."""
        raw, source = self.socket.recvfrom(4096)
        data, pid = self.decode(raw)
        return data, (source, pid)

    def close(self):
        """Close the link."""
        self.socket.close()

    @staticmethod
    def decode(raw):
        """Decode raw bytes to data."""
        packet = unpack(raw)
        return packet['data'], packet['id']

    @staticmethod
    def encode(data, pid=None):
        """Encode a packet to raw bytes."""
        packet = {
            'id': pid if pid else str(uuid4()),
            'data': data,
        }
        return pack(packet)

class MulticastReceiver(Link):
    """Recieve data from a multicast network."""

    def __init__(self, multicast_address, port):
        ip_address = IPv4Address(multicast_address)
        if not ip_address.is_multicast:
            raise ValueError('invalid multicast_address')

        super().__init__(multicast_address, port)

        sock = self.socket
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        mreq = struct.pack('4sl',
                           socket.inet_aton(self.address[0]),
                           socket.htonl(socket.INADDR_ANY))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        sock.bind(self.address)

    def close(self):
        sock = self.socket
        mreq = struct.pack('4sl',
                           socket.inet_aton(self.address[0]),
                           socket.htonl(socket.INADDR_ANY))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, mreq)
        super().close()

    send = property(doc='Disable send on multicast bound sockets.')
