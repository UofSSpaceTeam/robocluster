'''Alternate way to instantiate serial devices manually'''

from robocluster import SerialDevice
import asyncio
sDevice = SerialDevice('/dev/ttyACM0')

async def serial_test():
    '''Write a value to the device and read the response'''
    async with sDevice as ser:
        while True:
            print("writing...")
            await ser.write_packet("T")
            msg = await ser.read_packet()
            print(msg)

loop = asyncio.get_event_loop()
loop.create_task(serial_test())
loop.run_forever()
