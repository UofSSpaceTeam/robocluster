from robocluster import Device
# import robocluster.util; robocluster.util.DEBUG = True

deviceA = Device('deviceA', 'rover')
deviceB = Device('deviceB', 'rover')

@deviceA.on('*/request')
async def reply(event, data):
    sender = event.split('/')[0]
    await deviceA.send(sender, 'request', 1234)

@deviceB.task
async def get_data():
    data = await deviceB.request('deviceA', 'request')
    print(data)

deviceA.start()
deviceB.start()
deviceB.wait()
