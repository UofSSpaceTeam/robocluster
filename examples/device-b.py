from time import sleep, time

from robocluster import Device

device = Device('device-b', 'demo-device')

@device.task
async def hello():
    message = 'Hello World!'
    while True:
        await device.publish('hello', message)
        await device.sleep(1)

@device.every('100ms')
async def every():
    await device.publish('every', time())

device.run_forever()
