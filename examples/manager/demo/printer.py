'''Prints the random date from random_stream'''
from robocluster import Device

device = Device('printer', 'computer1')

@device.on('random-stream/random')
async def callback(event, data):
    '''Print the numbers'''
    print('Got ' + str(data))

device.run()
