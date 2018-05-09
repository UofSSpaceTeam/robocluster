import shlex
from subprocess import Popen
from threading import Thread
import time
import socket

from robocluster import Device

class RoboProcess:
    """Manages and keeps track of a process."""

    class RunnerThread(Thread):
        """Waits for the process to exit, and calls the on_exit callback."""

        def __init__(self, process, on_exit):
            super().__init__()
            self.process = process
            self.on_exit = on_exit


        def run(self):
            if self.process:
                returncode = self.process.wait()
                self.on_exit(returncode)

    def __init__(self, name, cmd, cwd=None, host=None):
        """
        Args:
            name (str): A name to identify the process by.
            cmd (str): The shell command to run.
        """
        if not isinstance(cmd, str):
            raise ValueError('command must be a string')
        self.name = name
        self.cmd = cmd
        self.pid = None
        self.process = None
        self.returncode = None
        self.killed = False
        self.cwd = cwd
        self.host = host

    def start(self):
        """ Start the process."""
        if not self.process:
            self.returncode = None
            args = shlex.split(self.cmd)
            if self.cwd is not None:
                self.process = Popen(args, cwd=self.cwd)
            else:
                self.process = Popen(args)
            self.runner = RoboProcess.RunnerThread(self.process, self.on_exit)
            self.runner.start()

    def stop(self, timeout=0):
        """ Stop the process. This sends SIGKILL, so not necessarily a gracefull exit."""
        if self.process:
            self.process.kill()
            self.killed = True
            self.runner.join(timeout)
            print('killed')

    def on_exit(self, returncode):
        """To be called when the process exits"""
        raise NotImplementedError('RoboProcess does not define a default behaivior on exit. Please inherit and define the on_exit(returncode) method')

class RunOnce(RoboProcess):
    """Run a process once, and don't restart after it exits."""

    def on_exit(self, returncode):
        self.process = None
        self.pid = None
        self.returncode = returncode


class RestartOnCrash(RoboProcess):
    """Restarts the process if it crashes."""

    def on_exit(self, returncode):
        self.process = None
        self.pid = None
        self.returncode = returncode
        if returncode != 0 and not self.killed:
            print('restart')
            self.start()

class ProcessManager:
    """
    Manages processes that run in the robocluster framework.

    Processes are programs that can run independently from each other, in any
    language supported by the robocluster library.

    The ProcessManager is responsible of creating, starting and stoping processes,
    and providing a remote API for other ProcessManagers to submit new processes.
    """

    def __init__(self, name=socket.gethostname(), network=None):
        """Initialize a process manager."""
        self.processes = {}
        self.remote_api = Device(name, 'Manager', network=network)
        self.name = name

        @self.remote_api.on('createProcess')
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

        @self.remote_api.on('stop')
        async def remote_stop(event, data):
            print('Got remote stop {}'.format(data))
            self.stop(data)

        @self.remote_api.on('start')
        async def remote_start(event, data):
            print('Got remote start {}'.format(data))
            self.start(data)

        @self.remote_api.task
        def rem_api_print():
            print('Remote API running')


    def __enter__(self):
        """Enter context manager"""
        self.remote_api.start()
        return self

    def __exit__(self, *exc):
        """Exit context manager, makes sure all processes are stopped"""
        self.stop()
        self.remote_api.stop()
        return False

    def createProcess(self, name, command):
        """
        Create a process.

        Arguments:
        name    - name to identify process, must be unique to process manager.
        command - shell command for process to execute.
        """
        self.addProcess(RoboProcess(name, command))

    def addProcess(self, roboprocess):
        """Adds roboprocess that was created externally to the manager"""
        if roboprocess.name in self.processes:
            raise VauleError('Process with the same name exists: {}'.format(roboprocess.name))
        self.processes[roboprocess.name] = roboprocess
        if roboprocess.host is not None:
            d = {
                'name':roboprocess.name,
                'command':roboprocess.cmd,
                'type':roboprocess.__class__.__name__
            }
            self.remote_api.send(roboprocess.host, 'CreateProcess', d)


    def start(self, *names):
        """
        Start processes.

        If no arguments are provided, starts all processes.
        """

        processes = names if names else self.processes.keys()
        for procname in processes:
            try:
                host = self.processes[procname].host
                if host is None:
                    print('Starting:', procname)
                    self.processes[procname].start()
                else:
                    self.remote_api.send(host, 'start', procname)
            except KeyError:
                print('Tried to start a process that doesnt exist')


    def stop(self, *names, timeout=1):
        """
        Stop processes.

        If no arguments are provided, stops all processes.
        """
        processes = names if names else self.processes.keys()
        for procname in processes:
            try:
                host = self.processes[procname].host
                if host is None:
                    print('Stopping:', procname)
                    self.processes[procname].stop(timeout)
                else:
                    self.remote_api.send(host, 'stop', procname)
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
