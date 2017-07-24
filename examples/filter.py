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
    subscriber.connect('tcp://localhost:5000')
    subscriber.subscribe(b'sensor')

    subscriber.connect('tcp://localhost:9000')
    subscriber.subscribe(b'EXIT')
    # }}}

    prev = 1.5

    try:
        while True:
            # {{{ Wrap this stuff
            topic, value = subscriber.recv_multipart()
            if topic == b'EXIT':
                print('Got {} command: {}'.format(topic.decode('utf8'),
                                                  value.decode('utf8')))
                return
            value = json.loads(value.decode('utf8'))
            # }}}
            prev = bayes_filter(prev, value)
            print('Raw: {}: Filtered: {}'.format(value, prev))
    except KeyboardInterrupt:
        print('Shutting down')

if __name__ == '__main__':
    main()
