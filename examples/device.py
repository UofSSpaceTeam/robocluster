from itertools import count
from time import time
from uuid import uuid4

from robocluster import Device

# random group so we don't collide in testing
group = str(uuid4())

device_a = Device('device-a', group)

@device_a.on('device-b/hello')
def hello(event, data):
    print(event, data)

@device_a.on('device-b/every')
def every(event, data):
    print(event, data)

device_b = Device('device-b', group)

@device_b.task
async def hello():
    counter = count()
    message = 'Hello World {}!'
    while True:
        await device_b.publish('hello', message.format(next(counter)))
        await device_b.sleep(1)

@device_b.every('100ms')
async def every():
    await device_b.publish('every', time())

try:
    device_a.start()
    device_b.start()
    device_a.wait()
    device_b.wait()
except KeyboardInterrupt:
    device_a.stop()
    device_b.stop()
