from robocluster import Device

device = Device('printer', 'computer1')

@device.on('random-stream/random')
async def callback(event, data):
    print('Got ' + str(data))

device.run()
