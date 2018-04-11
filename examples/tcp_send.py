from robocluster import Device
import robocluster.util; robocluster.util.DEBUG = True

sender = Device('sender', 'rover')
getter = Device('getter', 'rover')

@sender.every('1s')
async def send():
    await sender.send('getter', 'test', 1234)

@getter.on('*test')
async def callback(event, data):
    print("event {}, data {}".format(event, data))

try:
    sender.start()
    getter.start()
except KeyboardInterrupt:
    sender.stop()
    getter.stop()

