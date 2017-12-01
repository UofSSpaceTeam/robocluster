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
    async def publish():
        await device_b.publish(test_key, test_val)

    @device_a.on('device-b/{}'.format(test_key))
    async def callback(event, data):
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
    assert(recieved_message == True)

if __name__ == '__main__':
    test_pubsub()
