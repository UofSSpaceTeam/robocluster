
from robocluster import SerialDevice

driver = SerialDevice('/dev/ttyACM0', 'rover')

@driver.every('1s')
async def print_name():
    print(driver.name)


driver.run()
