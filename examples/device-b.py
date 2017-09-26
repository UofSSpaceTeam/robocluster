from time import sleep

from robocluster import Device

device = Device('device-b', ('224.0.0.64', 22464))

try:
    while True:
        device.publish('hello', 'Hello World!')
        sleep(1)
except KeyboardInterrupt:
    pass
