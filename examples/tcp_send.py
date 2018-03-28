from robocluster import Device
# import robocluster.util; robocluster.util.DEBUG = True

device = Device('test', 'rover')
device.create_egress_tcp('test') # This can be left out

@device.every('1s')
async def send():
    await device.send('test', 'test', 1234)

@device.on('*/test', ports='test_tcp')
async def callback(event, data):
    print("event {}, data {}".format(event, data))

device.run()
