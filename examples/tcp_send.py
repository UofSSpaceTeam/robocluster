from robocluster import Device
# import robocluster.util; robocluster.util.DEBUG = True

device = Device('test', 'rover')
device.create_tcp('test')

@device.every('1s')
async def send():
    await device.ports['test'].write({'event':'test', 'data':1234})

@device.on('test', ports='test')
async def callback(event, data):
    print("event {}, data {}".format(event, data))

device.run()
