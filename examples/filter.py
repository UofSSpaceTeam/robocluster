'''
Takes in any data from a sensor and filters it.
'''

import json
import zmq


def filter(prev, measured):
    ''' Super lame Bayes filter'''
    return (prev + measured)/2


def main():
    # {{{ wrap this stuff
    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)
    subscriber.connect("tcp://localhost:5000")
    subscriber.setsockopt(zmq.SUBSCRIBE, b"sensor")
    # }}}

    prev = 1.5

    try:
        while True:
            # {{{ combine these lines into one function
            [key, value] = subscriber.recv_multipart()
            value = json.loads(value.decode('utf8'))
            # }}}
            print("Raw: {}: Filtered: {}".format(value, filter(prev, value)))
            prev = value
    except KeyboardInterrupt:
        print("Shutting down")

if __name__ == '__main__':
    main()
