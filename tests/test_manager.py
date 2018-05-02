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

if __name__ == '__main__':
    test_add_process()
