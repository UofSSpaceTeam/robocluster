'''Demonstration of registering two serial
devices with one Device event loop
'''

from robocluster import Device

device = Device('link', 'rover')
micro = device.create_serial('/dev/ttyACM0')
teensy = device.create_serial('/dev/ttyACM1')
print(micro)
print(teensy)

@micro.on('micro')
async def callback(event, data):
    '''Callback for serial device 1'''
    print(event, data)

@teensy.on('teensy')
async def callback(event, data):
    '''Callback for serial device 2'''
    print(event, data)

device.run()
