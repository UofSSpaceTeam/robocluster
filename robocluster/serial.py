import serial_asyncio
import asyncio
import json

BAUDRATE = 115200


class SerialDevice:
    """
    A serial device that can optionally be integrated
    with the robocluster network.
    """

    def __init__(self, usbpath, pktformat='json', loop=None):
        self._loop = loop if loop else asyncio.get_event_loop()
        self._format = pktformat
        self._reader = None  # once initialized, an asyncio.StreamReader
        self._writer = None  # once initialized, an asyncio.StreamWriter
        self._usbpath = usbpath
        self._baudrate = BAUDRATE
        self._loop.create_task(self.init_serial())


    async def init_serial(self):
        """Initialize the StreamReader and StreamWriter."""
        self._reader, self._writer = await serial_asyncio.open_serial_connection(
                url=self._usbpath,
                baudrate=self._baudrate)

    def isInitialized(self):
        """Checks if the StreamReader and StreamWriter are initialized"""
        return self._reader and self._writer

    async def read_byte(self):
        """Read a single byte from the serial device"""
        if not self._reader:
            raise RuntimeError("Serial reader not initialized yet")
        b = await self._reader.read(1)
        return b

    async def read_packet(self):
        """
        Read a json packet from the serial device.
        Assumes the packet is a single dictionary and there
        are no nested dictionaries.
        """
        if not self._reader:
            raise RuntimeError("Serial reader not initialized yet")
        if self._format == 'json':
            pkt = await self._reader.readuntil(b'}')
            return json.loads(pkt)

        raise RuntimeError('Packet format type not supported')
