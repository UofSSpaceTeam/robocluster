from robocluster import Device


device = Device('link', 'rover')
# sDevice = device.create_serial('/dev/ttyACM0')
#
# @sDevice.on('test')
# async def callback(event, data):
#     print(event, data)
#
# device.run()

# Alternative method of serial device creation
from robocluster import SerialDevice
import asyncio
sDevice = SerialDevice('/dev/ttyACM0', loop=device._loop)
# device.link_serial(sDevice)

async def serial_read():
    async with sDevice as ser:
        while True:
            print('reading')
            msg = await ser.read_packet()
            print(msg)

@device.task
async def serial_write():
    async with sDevice as ser:
        while True:
            print('writing')
            await ser.write_packet("T")
            msg = await ser.read_packet()
            print(msg)

# loop = asyncio.get_event_loop()
# loop.create_task(serial_read())
# loop.create_task(serial_write())
# loop.run_forever();
device.run()
