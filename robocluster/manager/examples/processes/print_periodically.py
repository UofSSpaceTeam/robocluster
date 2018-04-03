'''Print stuff periodically
Ussage: print_periodically.py <print_interval> <exit-time>
'''
import sys
import time

import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('print_periodically')

if __name__ == '__main__':
    print_every = int(sys.argv[1])
    exit_at = int(int(sys.argv[2])/print_every)
    for i in range(exit_at):
        log.info('The time is {}'.format(time.time()))
        time.sleep(print_every)
