import time
import asyncio

from robocluster.manager import RunOnce

def test_RunOnce():
    proc = RunOnce('echo-test', 'echo "Hello world"')
    async def run_proc():
        await proc.run()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_proc())

if __name__ == '__main__':
    test_RunOnce()
