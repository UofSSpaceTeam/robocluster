"""THIS FILE IS SUBJECT TO THE LICENSE TERMS GRANTED BY THE UNIVERSITY OF SASKATCHEWAN SPACE TEAM (USST)."""

import shlex
import sys
from subprocess import Popen
from time import sleep

class RoboProcess:
    """Manages and keeps track of a process."""

    def __init__(self, cmd):
        """Initialize a process containing command cmd."""
        self.cmd = cmd
        self.popen = None

    def start(self):
        """
        Start the process.

        Ignored if process is already running.
        """
        if not self.popen:
            args = shlex.split(self.cmd)
            self.popen = Popen(args)

    def stop(self):
        """
        Stop the process.

        Ignored if the process is not running.
        """
        if self.popen:
            self.popen.terminate()
            try:
                self.popen.wait(timeout=1)
            except TimeoutError:
                self.popen.kill()
                self.popen.wait()
            self.popen = None

    def status(self):
        """Return the status of a process."""
        raise NotImplementedError()

    def verify(self):
        """Verify if a process is running properly."""
        raise NotImplementedError()

    def fix(self):
        """Fix a process if its not running properly."""
        raise NotImplementedError()

class ProcessManager:
    """
    Manages processes that run in the robocluster framework.

    Processes are programs that can run independently from each other, in any
    language supported by the robocluster library.

    The ProcessManager is in charge of starting and stopping processes, and
    monitoring their status and handle the event of a crash or a process not
    responding.
    """

    def __init__(self):
        """Initialize a process manager."""
        self.processes = {}  # store processes by name

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, *exc):
        """Exit context manager, makes sure all processes are stopped."""
        self.stop()
        return False

    def isEmpty(self):
        """Return if processes is empty."""
        return len(self.processes) == 0

    def createProcess(self, name, command):
        """
        Create a process.

        Arguments:
        name    - name to identify process, must be unique to process manager.
        command - shell command for process to execute.
        """
        if name in self.processes:
            raise ValueError('Process with the same name exists: {name}')

        if not isinstance(command, str):
            raise ValueError('command must be a string')

        self.processes[name] = RoboProcess(command)


    def start(self, *names):
        """
        Start processes.

        If no arguments are provided, starts all processes.
        """
        processes = names if names else self.processes.keys()
        for process in processes:
            try:
                print('Starting:', process)
                self.processes[process].start()
            except KeyError:
                pass

    def stop(self, *names):
        """
        Stop processes.

        If no arguments are provided, stops all processes.
        """
        processes = names if names else self.processes.keys()
        for process in processes:
            try:
                print('Stopping:', process)
                self.processes[process].stop()
            except KeyError:
                pass


def main():
    """Run a process manager in the foreground."""
    process_names = [
        ["sleep", "python sleeper.py"],
        ["crash", "python crash.py"],
    ]

    with ProcessManager() as manager:
        """Initialize all the processes"""
        for proc in process_names:
            manager.createProcess(*proc)

        manager.start()

        try:
            while True:
                # TODO: Verify processes.
                sleep(1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    exit(main())
