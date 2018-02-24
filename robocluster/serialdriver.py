import asyncio
import json

import pyvesc
import serial
import serial_asyncio

from .device import Device
from .util import debug
from .message import Message
from .ports.serial import SerialPort


class SerialDriver(Device):
    """Device that exposes a serial device to the robocluster network."""

    def __init__(self, name, group, loop=None, encoding='json', disable_receive_loop=False):
        super().__init__(name, group, loop=loop)
        self.serial_port = SerialPort(name,
                encoding=encoding, loop=self._loop,
                disable_receive_loop=disable_receive_loop)
        self.serial_port.on_recv('send', self.handle_packet)
        self.serial_port.on_recv('publish', self.handle_packet)
        self.serial_port.on_recv('heartbeat', self.handle_packet)
        self.encoding = encoding
        self._router.on_message(self.forward_packet)
        self.serial_port.start()

    async def handle_packet(self, other, message):
        """Forward messages from serial to robocluster network."""
        if message.type == 'heartbeat':
            self.name = message.source
            self._router.name = self.name
        if self.encoding == 'json': #TODO: support VESC/binary?
            await self._router.route_message(message)

    async def forward_packet(self, packet):
        """Forwards messages from robocluster network to serial device."""
        await self.serial_port.send(packet.to_json())

    async def write(self, data):
        """Write to the serial device."""
        #TODO: the message creation is wrong...
        if self.encoding == 'json':
            msg = Message(self.name, 'publish', data)
        elif self.encoding == 'vesc':
            msg = data
        await self.serial_port.send(msg)
