'''Demonstration of interacting with
a VESC device.
'''
from robocluster import Device
from pyvesc import BlinkLed


device = Device('link', 'rover')
serial = device.create_serial('/dev/ttyACM0', encoding='vesc')

blink_val = 0

@serial.on('ExampleSendMessage')
async def callback(event, data):
    '''Print string that was sent and toggle LED'''
    global blink_val
    print(data.string)
    await serial.write_packet(BlinkLed(blink_val))
    blink_val = not blink_val

device.run()
