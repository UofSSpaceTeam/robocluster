import time
import pty
import os
import json

import pyvesc
from pyvesc import ExampleSendMessage
import robocluster.util; robocluster.util.DEBUG = True

from robocluster import SerialDriver, Device

def test_serial_write():
    # Create pseuto-terminals
    # Only works on Unix systems...
    master, slave = pty.openpty()

    device = SerialDriver(os.ttyname(slave), 'tester')

    TEST_DATA = {'test': 'value'}

    @device.task
    async def write_ser():
        await device.write(TEST_DATA)
        print("done write")

    device.start()
    time.sleep(0.2)
    msg = os.read(master, 100)
    print(msg)
    assert(json.loads(msg.decode('utf-8'))['data'] == TEST_DATA)
    device.stop()

def test_serial_read():
    master, slave = pty.openpty()

    serial = SerialDriver(os.ttyname(slave), 'tester')
    device = Device('test', 'tester')
    device.storage.msg_received = False

    TEST_DATA = {'test': 'value'}

    @device.on('*/test')
    async def callback(event, data):  # pylint: disable=W0612
        assert(data == TEST_DATA)
        print("Got data {}".format(data))
        device.storage.msg_received = True

    serial.start()
    device.start()
    time.sleep(0.1)
    packet = {
        'source': 'tester',
        'type': 'publish',
        'data': {
            'topic': 'test',
            'data': TEST_DATA
        }
    }
    os.write(master, json.dumps(packet).encode('utf8'))
    time.sleep(0.1)
    device.stop()
    serial.stop()
    assert(device.storage.msg_received)

def test_vesc_write():
    # Same as test_serial_write but with vesc data
    master, slave = pty.openpty()

    device = SerialDriver(os.ttyname(slave), 'tester', encoding='vesc')

    TEST_MSG = 'Hello world'
    TEST_DATA = ExampleSendMessage(TEST_MSG)

    @device.task
    async def write_ser():
        await device.write(TEST_DATA)
        print("done write")

    device.start()
    time.sleep(0.2)
    data = os.read(master, 100)
    print(data)
    msg, _ = pyvesc.decode(data)
    assert(msg.string == TEST_MSG)
    device.stop()

if __name__ ==  '__main__':
    test_vesc_write()
