from time import time

from robocluster import Device

device = Device('device-b', 'demo-device')

@device.task
async def hello():
    print('start')
    message = 'Hello World!'
    while True:
        await device.publish('hello', message)
        print('publish:', message)
        await device.sleep(1)

@device.every('100ms')
async def every():
    now = time()
    await device.publish('every', now)
    print('publish:', now)

device.start()
device.wait()
