'''
Simulates sensor data by generating random numbers.
'''

from random import randrange
import json
import time
import zmq


def main():
    context = zmq.Context()

    publisher = context.socket(zmq.PUB)
    publisher.bind("tcp://*:5000")

    try:
        while True:
            publisher.send_multipart(["sensor".encode(),
                                     json.dumps(randrange(133, 255)/100).encode()])
            time.sleep(0.001)
    except KeyboardInterrupt:
        print("Shutting down")

if __name__ == '__main__':
    main()
