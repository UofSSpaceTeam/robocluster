from robocluster import Device
from pyvesc import BlinkLed


device = Device('link', 'rover')
sDevice = device.create_serial('/dev/ttyACM0', pktformat='vesc')

blink_val = 0

@sDevice.on('test')
async def callback(event, data):
    print(event, data)

@sDevice.on('ExampleSendMessage')
async def callback(event, data):
    global blink_val
    print(data.string)
    await sDevice.write_packet(BlinkLed(blink_val))
    blink_val = not blink_val

device.run()
