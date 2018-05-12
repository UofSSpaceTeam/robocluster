import time


from robocluster.manager import RunOnce, ProcessManager

def test_RunOnce():
    proc = RunOnce('echo-test', 'echo "Hello world"')
    proc.start()
    time.sleep(0.5)
    assert proc.returncode == 0

def test_add_process():
    proc = RunOnce('echo-test', 'echo "Hello world"')
    manager = ProcessManager()
    manager.addProcess(proc)
    assert('echo-test' in manager.processes)

def test_start_manager():
    #TODO: actually test things?
    proc = RunOnce('echo-test', 'echo "Hello world"')
    with ProcessManager() as manager:
        manager.addProcess(proc)
        manager.start()
        time.sleep(1)


if __name__ == '__main__':
    test_add_process()
