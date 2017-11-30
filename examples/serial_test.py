'''Barebones example of how to register a
callback for events sent by the serial device.
'''

from robocluster import Device

device = Device('link', 'rover')
sDevice = device.create_serial('/dev/ttyACM0')


@sDevice.on('test')
async def callback(event, data):
    '''Print the event and value'''
    print(event, data)

device.run()
