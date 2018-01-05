from uuid import uuid4
import random
from time import sleep, time

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
    last_time = time()
    loop_delay = 0

    @device_a.every(0.01)
    async def loop():  # pylint: disable=W0612
        nonlocal counter, last_time, loop_delay
        # measure period of loop
        curr_time = time()
        loop_delay = curr_time-last_time
        last_time = curr_time

        counter += 1
        if counter == 2:
            # we've ran a few times at least
            device_a.stop()

    device_a.start()
    sleep(0.04)
    device_a.stop()
    assert(counter == 2)
    tolerance = 0.01
    assert(loop_delay - 0.01 < tolerance)

def test_send():
    group = str(uuid4())
    device_a = Device('device_a', group)
    device_b = Device('device_b', group)
    message_received = False

    TEST_DATA = {'key': 'Hello', 'values': 1234}

    @device_b.on('*/direct-msg')
    async def callback(event, data):  # pylint: disable=W0612
        nonlocal message_received
        print('device_b got message')
        assert(event == 'device_a/direct-msg')
        assert(data == TEST_DATA)
        message_received = True

    @device_a.task
    async def send_msg():  # pylint: disable=W0612
        print('device_a sending message')
        await device_a.send('device_b', 'direct-msg', TEST_DATA)

    device_b.start()
    device_a.start()
    print('devices started')
    sleep(0.05)
    device_a.stop()
    device_b.stop()
    print('done sleep')
    assert(message_received)

def test_storage():
    device = Device('device', 'test')
    device.storage.counter = 0

    @device.every('20ms')
    async def increment():  # pylint: disable=W0612
        device.storage.counter += 1

    device.start()
    sleep(0.11)
    device.stop()
    assert(device.storage.counter == 6)

def test_request():
    deviceA = Device('deviceA', 'rover')
    deviceB = Device('deviceB', 'rover')
    deviceB.storage.message_received = False

    TEST_DATA = 1234

    @deviceA.on('*/request')
    async def reply(event, data):  # pylint: disable=W0612
        await deviceA.reply(event, TEST_DATA)

    @deviceB.task
    async def get_data():  # pylint: disable=W0612
        data = await deviceB.request('deviceA', 'request')
        assert(data == TEST_DATA)
        print(data)
        deviceB.storage.message_received = True

    deviceA.start()
    deviceB.start()
    sleep(0.1)
    deviceB.stop()
    deviceA.stop()
    assert(deviceB.storage.message_received)


