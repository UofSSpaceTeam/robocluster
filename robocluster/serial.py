import serial_asyncio
import asyncio
import json

BAUDRATE = 115200


class SerialDevice:

    def __init__(self, usbpath, pktformat='json', loop=None):
        self._loop = loop if loop else asyncio.get_event_loop()
        self._format = pktformat
        self._reader = None  # once initialized, an asyncio.StreamReader
        self._writer = None  # once initialized, an asyncio.StreamWriter
        self._loop.create_task(self._get_serial(usbpath, BAUDRATE))


    async def _get_serial(self, usbpath, baudrate):
        self._reader, self._writer = await serial_asyncio.open_serial_connection(
                url=usbpath,
                baudrate=baudrate)

    def isInitialized(self):
        return self._reader is not None and self._writer is not None

    async def read_byte(self):
        if self._reader is None:
            raise RuntimeError("Serial reader not initialized yet")
        b = await self._reader.read(1)
        return b

    async def read_packet(self):
        if self._reader is None:
            raise RuntimeError("Serial reader not initialized yet")
        if self._format == 'json':
            pkt = await self._reader.readuntil(b'}')
            return json.loads(pkt)

        raise RuntimeError('Packet format type not supported')
