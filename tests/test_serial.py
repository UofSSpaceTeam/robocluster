import time
import pty
import os
import json

from robocluster import Device

def test_serial_write():
    # Create pseuto-terminals
    # Only works on Unix systems...
    master, slave = pty.openpty()

    device = Device('test', 'tester')
    sDevice = device.create_serial(os.ttyname(slave))

    TEST_DATA = {'test': 'value'}

    @device.task
    async def write_ser():
        await device.ports[os.ttyname(slave)].write(TEST_DATA)
        print("done write")

    device.start()
    time.sleep(1)
    msg = os.read(master, 100)
    print(msg)
    assert(json.loads(msg.decode('utf-8')) == TEST_DATA)
    device.stop()

if __name__ ==  '__main__':
    test_serial_write()
