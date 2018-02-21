import asyncio
import json

import pyvesc
import serial
import serial_asyncio

from .device import Device
from .util import debug
from .router import Message


class SerialDriver(Device):
    """Device that exposes a serial device to the robocluster network."""

    def __init__(self, name, group, loop=None, encoding='json', disable_receive_loop=False):
        super().__init__(name, group, loop=loop)
        self.serial_connection = SerialConnection(name,
                encoding=encoding, loop=self._loop,
                disable_receive_loop=disable_receive_loop)
        self.serial_connection.packet_callback = self.handle_packet
        self.encoding = encoding
        self._router.on_message(self.forward_packet)

    async def handle_packet(self, message):
        """Forward messages from serial to robocluster network."""
        print(message)
        if message.type == 'heartbeat':
            self.name = message.source
            self._router.name = self.name
        if self.encoding == 'json': #TODO: support VESC/binary?
            await self._router.route_message(message)

    async def forward_packet(self, packet):
        """Forwards messages from robocluster network to serial device."""
        await self.serial_connection.write(packet.to_json())

    async def write(self, data):
        """Write to the serial device."""
        await self.serial_connection.write(data)

    async def read(self, num_bytes=1):
        """Read a byte from the serial device"""
        return self.serial_connection.read(num_bytes)
