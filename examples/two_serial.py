'''Demonstration of registering two serial
devices with one Device event loop
'''

from robocluster import Device

device = Device('link', 'rover')
device.create_serial('/dev/ttyACM0')
device.create_serial('/dev/ttyACM1')

@device.on('micro')
async def micro_callback(event, data):
    '''Callback for serial device 1'''
    print(event, data)

@device.on('teensy')
async def teensy_callback(event, data):
    '''Callback for serial device 2'''
    print(event, data)

device.run()
