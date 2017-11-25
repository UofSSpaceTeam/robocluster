'''Connects to a serial device and prints data from it.'''
from robocluster import Device

device = Device('link', 'rover')
sDevice = device.create_serial('/dev/ttyACM0')


@sDevice.on('test')
async def callback(event, data):
    '''Print the event and value'''
    print(event, data)

device.run()
