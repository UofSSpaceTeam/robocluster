import asyncio

from robocluster import Device

device = Device('device-a', 'demo-device')

@device.on('device-b/hello')
def hello(event, data):
    print(event, data)

@device.on('device-b/every')
def every(event, data):
    print(event, data)

device.start()
device.context.wait()
