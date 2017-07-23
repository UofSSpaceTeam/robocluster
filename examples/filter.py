'''
Takes in any data from a sensor and filters it.
'''

import json
import zmq


def bayes_filter(prev, measured):
    ''' Super lame Bayes filter'''
    return (prev + measured)/2


def main():
    # {{{ wrap this stuff
    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)
    subscriber.connect("tcp://localhost:5000")
    subscriber.setsockopt(zmq.SUBSCRIBE, b"sensor")

    kill_sig = context.socket(zmq.SUB)
    kill_sig.connect("tcp://localhost:9000")
    kill_sig.setsockopt(zmq.SUBSCRIBE, b"EXIT")
    # }}}

    prev = 1.5

    try:
        while True:
            # {{{ wrap this stuff
            try:  # Replace with polling?
                kill_sig.recv(flags=zmq.NOBLOCK)
                print("Got exit command")
                return
            except zmq.ZMQError:
                pass
            # }}}
            # {{{ combine these lines into one function
            [_, value] = subscriber.recv_multipart()
            value = json.loads(value.decode('utf8'))
            prev = bayes_filter(prev, value)
            # }}}
            print("Raw: {}: Filtered: {}".format(value, prev))
    except KeyboardInterrupt:
        print("Shutting down")

if __name__ == '__main__':
    main()
