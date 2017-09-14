# THIS FILE IS SUBJECT TO THE LICENSE TERMS GRANTED BY THE UNIVERSITY OF SASKATCHEWAN SPACE TEAM (USST).

import time
import sys
from subprocess import Popen
import shlex


class RoboProcess:
    """Manages and keeps track of a process."""

    def __init__(self, cmd):
        """Initialize a process containing command cmd."""
        self.cmd = cmd
        self.popen = None

    def execute(self):
        """Run the process's command."""
        args = shlex.split(self.cmd)
        self.popen = Popen(args)


class ProcessManager:
    """
    Manages processes that run in the robocluster framework.

    Processes are just programs that can run independantly
    from each other, in any language supported by the robocluster library.
    The ProcessManager is in charge of starting and stopping processes,
    and monitering their status and handle the event of a crash
    or a process not responding.
    """

    def __init__(self):
        """Initialize a process manager."""
        # process dictionary stores RoboProcess instances indexed
        # by the process name
        self.processes = {}

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, *exc):
        """Exit context manager, makes sure all processes are stopped."""
        self.stopAllProcesses()
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
            raise ValueError(f'Process with the same name exists: {name}')

        if not isinstance(command, str):
            raise ValueError('command must be a string')

        self.processes[name] = RoboProcess(command)

    # TODO: Do we really need this if we have createProcess?
    def createThread(self):
        """
        TODO create a function that takes in parameters and uses those parameters to
        ceate one single thread. The thread must then be stored in "self.T".
        """
        pass

    def startProcess(self, name):
        """Start a single process."""
        print('Starting {}'.format(name))
        self.processes[name].execute()

    def startAllProcesses(self):
        """Start all managed processes."""
        for process in self.processes:
            self.startProcess(process)

    def stopProcess(self, name):
        """Stop a process by name."""
        print ("Shutting down " + name)
        self.processes[name].popen.kill()
        self.processes[name].popen.wait()

    def stopAllProcesses(self):
        """Stop all managed processes."""
        print ("Shutting down")
        for process in self.processes:
            self.stopProcess(process)

    def status(self, thread):
        """Return the status of a thread or process."""
        raise NotImplementedError()

    def verify(self, thread):
        """Verify if a thread of process is running properly."""
        raise NotImplementedError()

    def fix(self, thread):
        """Fix a thread or process if its not running properly."""
        raise NotImplementedError()


def main():
    """Run a process manager in the foreground."""
    process_names = [["sleep", "python sleeper.py"],
                     ["crash", "python crash.py"]]
    # Once the threading module is working fine, then we can begin connecting the proceses through 0mq.
    with ProcessManager() as manager:
        # Initialize all the processes
        for proc in process_names:
            manager.createProcess(*proc)

        manager.startAllProcesses()

        try:
            while True: # Execute the processes.
                # TODO Run the processes as they should.
                for task in manager.processes: # Verify tasks.
                    # taskMgr.verify(task.name)
                    pass
                time.sleep(3)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    exit(main())
