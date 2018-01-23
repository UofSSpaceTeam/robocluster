import time
import pty
import os
import json

import pyvesc
from pyvesc import ExampleSendMessage

from robocluster import Device

def test_serial_write():
    # Create pseuto-terminals
    # Only works on Unix systems...
    master, slave = pty.openpty()

    device = Device('test', 'tester')
    device.create_serial(os.ttyname(slave))

    TEST_DATA = {'test': 'value'}

    @device.task
    async def write_ser():
        await device.ports[os.ttyname(slave)].write(TEST_DATA)
        print("done write")

    device.start()
    time.sleep(0.2)
    msg = os.read(master, 100)
    print(msg)
    assert(json.loads(msg.decode('utf-8')) == TEST_DATA)
    device.stop()

def test_serial_read():
    master, slave = pty.openpty()

    device = Device('test', 'tester')
    device.create_serial(os.ttyname(slave))
    device.storage.msg_received = False

    TEST_DATA = {'test': 'value'}

    @device.on('test')
    async def callback(event, data):  # pylint: disable=W0612
        assert(data == TEST_DATA)
        print("Got data {}".format(data))
        device.storage.msg_received = True

    device.start()
    time.sleep(0.1)
    packet = {
        'type': 'send',
        'event': 'test',
        'data': TEST_DATA
    }
    os.write(master, json.dumps(packet).encode('utf8'))
    time.sleep(0.1)
    device.stop()
    assert(device.storage.msg_received)

def test_vesc_write():
    # Same as test_serial_write but with vesc data
    master, slave = pty.openpty()

    device = Device('test', 'tester')
    device.create_serial(os.ttyname(slave), encoding='vesc')

    TEST_MSG = 'Hello world'
    TEST_DATA = ExampleSendMessage(TEST_MSG)

    @device.task
    async def write_ser():
        await device.ports[os.ttyname(slave)].write(TEST_DATA)
        print("done write")

    device.start()
    time.sleep(0.2)
    data = os.read(master, 100)
    print(data)
    msg, _ = pyvesc.decode(data)
    assert(msg.string == TEST_MSG)
    device.stop()

if __name__ ==  '__main__':
    test_serial_write()
