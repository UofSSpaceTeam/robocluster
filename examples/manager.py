'''
Waits for a keyboard interupt, and sends a kill signal to the other nodes
'''

import time
import zmq


def main():
    context = zmq.Context()
    shutdown = context.socket(zmq.PUB)
    shutdown.bind("tcp://*:9000")

    shutdown.send(b'START')
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Sending kill signal")
        shutdown.send(b"EXIT")
        return

if __name__ == '__main__':
    main()
