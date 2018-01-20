import asyncio

from robocluster.loop import LoopThread
from robocluster.router import Router

async def amain(args):
    with Router(args.name, args.group, args.port) as r:
        r.start()
        r.subscribe('*/hello', print)
        while True:
            await r.publish('hello', {'hello': 'world'})
            await asyncio.sleep(1)

def main(args):
    args = parse_args(args)

    thread = LoopThread()
    thread.start()

    thread.create_task(amain(args))

    try:
        thread.join()
    except KeyboardInterrupt:
        thread.stop()

def parse_args(args):
    import argparse as ag

    parser = ag.ArgumentParser()

    parser.add_argument('name')
    parser.add_argument('--group', default='224.0.0.1')
    parser.add_argument('--port', default=12345)

    return parser.parse_args()


if __name__ == '__main__':
    import sys
    exit(main(sys.argv[1:]))
