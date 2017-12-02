from uuid import uuid4
import random
from time import sleep

from robocluster import Device

def test_pubsub():
    # random group so we don't collide in testing
    group = str(uuid4())

    test_val = random.random()
    test_key = 'test'
    recieved_message = False
    device_a = Device('device-a', group)
    device_b = Device('device-b', group)

    @device_b.task
    async def publish():  # pylint: disable=W0612
        await device_b.publish(test_key, test_val)

    @device_a.on('device-b/{}'.format(test_key))
    async def callback(event, data):  # pylint: disable=W0612
        nonlocal recieved_message
        assert(event == 'device-b/{}'.format(test_key))
        assert(data == test_val)
        recieved_message = True
        print(recieved_message)

    device_a.start()
    device_b.start()
    sleep(0.01)
    device_a.stop()
    device_b.stop()
    assert(recieved_message)

def test_every():
    # random group so we don't collide in testing
    group = str(uuid4())
    device_a = Device('device_a', group)
    counter = 0

    @device_a.every(0.01)
    async def loop():  # pylint: disable=W0612
        nonlocal counter
        counter += 1

    device_a.start()
    sleep(0.02)
    device_a.stop()
    assert(counter == 2)
