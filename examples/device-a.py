from rcluster import Device

device = Device('device-a', ('224.0.0.64', 22464))

@device.on('device-b/hello')
def hello_1(data):
    print('first handler for device-b/hello:', data)

@device.on('device-b/hello')
def hello_2(data):
    print('second handler for device-b/hello:', data)

device.run()
