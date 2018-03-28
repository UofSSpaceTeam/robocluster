'''Demonstration of interacting with
a VESC device.
'''
from robocluster import Device
from pyvesc import BlinkLed
# import robocluster.util; robocluster.util.DEBUG = True


device = Device('link', 'rover')
usbpath = '/dev/ttyACM0'
device.create_serial(usbpath, encoding='vesc')

blink_val = 0

@device.on('ExampleSendMessage')
async def callback(event, data):
    '''Print string that was sent and toggle LED'''
    global blink_val
    print(data.string)
    await device.ports[usbpath].write(BlinkLed(blink_val))
    blink_val = not blink_val

device.run()
