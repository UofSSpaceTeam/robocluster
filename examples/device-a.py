from robocluster import Device

device = Device('device-a', '224.0.0.64:32464')

@device.on('device-b/hello')
async def hello(event, data):
    print(event, data)

@device.on('device-b/every')
async def every(event, data):
    print(event, data)

device.run_forever()
