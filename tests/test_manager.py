import asyncio

from robocluster.manager import RunOnce, ProcessManager

def test_RunOnce():
    proc = RunOnce('echo-test', 'echo "Hello world"')
    async def run_proc():
        await proc.run()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_proc())

def test_add_process():
    proc = RunOnce('echo-test', 'echo "Hello world"')
    manager = ProcessManager()
    manager.addProcess(proc)
    assert('echo-test' in manager.processes)

if __name__ == '__main__':
    test_add_process()
