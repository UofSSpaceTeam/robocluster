from robocluster import Device


device = Device('link', 'rover')
sDevice = device.create_serial('/dev/ttyACM0')

@sDevice.on('test')
async def callback(event, data):
    print(event, data)

device.run()

# Alternative method of serial device creation
# from robocluster import SerialDevice
# import asyncio
# sDevice = SerialDevice('/dev/ttyACM0')
# device.link_serial(sDevice)

# async def serial_read():
#     async with sDevice as ser:
#         while True:
#             msg = await ser.read_packet()
#             print(msg)
#
# loop = asyncio.get_event_loop()
# loop.run_until_complete(serial_read())
