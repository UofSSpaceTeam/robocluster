import asyncio

from robocluster import Device

device = Device('device-a', 'demo-device')

@device.on('device-b/hello')
def hello(event, data):
    print(event, data)

@device.on('device-b/every')
def every(event, data):
    print(event, data)

@device.every('1s')
def beat():
    print(device._member._peers)

device.start()
device.context.wait()
