from robocluster.serial import SerialDevice
import asyncio


device  = SerialDevice('/dev/ttyACM0')

async def read_data():
    while not device.isInitialized():
        asyncio.sleep(0.01)

    msg = await device.read_packet()
    print(msg)

loop = asyncio.get_event_loop()

loop.run_until_complete(read_data())
