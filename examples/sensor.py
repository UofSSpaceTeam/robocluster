'''
Simulates sensor data by generating random numbers.
'''

from random import randrange
import json
import time
import zmq


def main():
    # {{{ wrap this stuff
    context = zmq.Context()

    publisher = context.socket(zmq.PUB)
    publisher.bind("tcp://*:5000")

    kill_sig = context.socket(zmq.SUB)
    kill_sig.connect("tcp://localhost:9000")
    kill_sig.setsockopt(zmq.SUBSCRIBE, b"EXIT")
    # }}}

    try:
        while True:
            try:  # Replace with polling?
                kill_sig.recv(flags=zmq.NOBLOCK)
                print("Got exit command")
                return
            except zmq.ZMQError:
                pass
            # Make this line way simpler.
            publisher.send_multipart(["sensor".encode(),
                                 json.dumps(randrange(133, 255)/100).encode()])
            time.sleep(0.001)
    except KeyboardInterrupt:
        print("Shutting down")

if __name__ == '__main__':
    main()
