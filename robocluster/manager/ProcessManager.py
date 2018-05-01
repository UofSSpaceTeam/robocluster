import shlex
from subprocess import Popen
from threading import Thread
import time

from robocluster import Device

class RoboProcess:

    class RunnerThread(Thread):

        def __init__(self, process, on_exit):
            super().__init__()
            self.process = process
            self.on_exit = on_exit


        def run(self):
            if self.process:
                returncode = self.process.wait()
                self.on_exit(returncode)

    def __init__(self, name, cmd):
        if not isinstance(cmd, str):
            raise ValueError('command must be a string')
        self.name = name
        self.cmd = cmd
        self.pid = None
        self.process = None
        self.killed = False

    def start(self):
        if not self.process:
            args = shlex.split(self.cmd)
            self.process = Popen(args)
            self.runner = RoboProcess.RunnerThread(self.process, self.on_exit)
            self.runner.start()

    def stop(self, timeout=0):
        if self.process:
            self.process.kill()
            self.killed = True
            self.runner.join(timeout)
            print('killed')

    def on_exit(self, returncode):
        """To be called when the process exits"""
        raise NotImplementedError('RoboProcess does not define a default behaivior on exit. Please inherit and define the on_exit(returncode) method')

class RunOnce(RoboProcess):

    def on_exit(self, returncode):
        self.process = None


class RestartOnCrash(RoboProcess):

    def on_exit(self, returncode):
        self.process = None
        if returncode != 0 and not self.killed:
            print('restart')
            self.start()

class ProcessManager:

    def __init__(self):
        self.processes = {}
        self.remote_api = Device('remote-api', 'Manager')

        @self.remote_api.on('*/createProcess')
        async def remote_createProcess(event, data):
            print('Got remote createProcess({})'.format(data))
            name = data['name']
            command = data['command']
            if data['type']:
                try:
                    proc = globals()[data['type']](name, command)
                    self.addProcess(proc)
                except AttributeError:
                    print('ERROR: invalid process type')
                    return
            else:
                print('Createing default process type')
                self.createProcess(name, command)
            self.start(name)

        @self.remote_api.on('*/stop')
        async def remote_stop(event, data):
            print('Got remote stop {}'.format(data))
            self.stop(data)

        @self.remote_api.on('*/start')
        async def remote_start(event, data):
            print('Got remote start {}'.format(data))
            self.start(data)

        @self.remote_api.task
        def rem_api_print():
            print('Remote API running')


    def __enter__(self):
        self.remote_api.start()
        return self

    def __exit__(self, *exc):
        self.stop()
        self.remote_api.stop()
        return False

    def createProcess(self, name, command):
        self.addProcess(RoboProcess(name, command))

    def addProcess(self, roboprocess):
        if roboprocess.name in self.processes:
            raise VauleError('Process with the same name exists: {}'.format(roboprocess.name))
        self.processes[roboprocess.name] = roboprocess


    def start(self, *names):

        processes = names if names else self.processes.keys()
        for process in processes:
            try:
                print('Starting:', process)
                self.processes[process].start()
            except KeyError:
                print('Tried to start a process that doesnt exist')


    def stop(self, *names, timeout=1):
        processes = names if names else self.processes.keys()
        for process in processes:
            try:
                print('Stopping:', process)
                self.processes[process].stop(timeout)
            except KeyError:
                print('Tried to stop a process that doesnt exist')

    


def test_procman():
    # processes = [
    #     RunOnce('sleep_exit', 'python ./sleep_exit.py'),
    #     RestartOnCrash('crasher', 'python crasher.py'),
    # ]
    processes = [
        RunOnce('printer', '/usr/bin/python3 demo/printer.py'),
        RunOnce('random_stream', '/usr/bin/python3 demo/random_stream.py'),
    ]
    with ProcessManager() as manager:
        for proc in processes:
            manager.addProcess(proc)

        manager.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
            


def test_RunOnce():
    proc = RunOnce('sleep_exit', 'python3 ./sleep_exit.py')
    proc.start()
    time.sleep(3)
    proc.stop()
    time.sleep(2)
    proc.start()

def test_restartCrash():
    proc = RestartOnCrash('crasher', 'python ./crasher.py')
    proc.start()
    time.sleep(4)
    proc.stop()


if __name__ == '__main__':
    test_procman()
