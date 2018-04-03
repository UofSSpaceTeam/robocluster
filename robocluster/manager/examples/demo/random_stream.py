'''Publish a stream of random data'''
from robocluster import Device
import random

device = Device('random-stream', 'computer1')

@device.every('10 ms')
async def generate():
    '''Generate the numbers'''
    await device.publish('random', random.random())

device.run()
