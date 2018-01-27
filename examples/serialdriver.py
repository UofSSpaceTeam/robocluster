
from robocluster import SerialDriver, Device
# import robocluster.util; robocluster.util.DEBUG = True

driver = SerialDriver('/dev/ttyACM0', 'rover')
tester = Device('tester', 'rover')

@tester.every('1s')
async def publish_data():
    await tester.publish('testSerial', 27)

@tester.on('*/sensor1')
def print_sensor(event, data):
    print('Sensor 1 data: {}'.format(data))


try:
    driver.start()
    tester.start()
    driver.wait()
    tester.wait()
except KeyboardInterrupt:
    driver.stop()
    tester.stop()

