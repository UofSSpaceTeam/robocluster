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

    Processes are just programs that can run independantly
    from each other, in any language supported by the robocluster library.
    The ProcessManager is in charge of starting and stopping processes,
    and monitoring their status and handle the event of a crash
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
            raise ValueError(f'Process with the same name exists: {name}')

        if not isinstance(command, str):
            raise ValueError('command must be a string')

        self.processes[name] = RoboProcess(command)


    def start(self,**name):
        """
        Starts processes

        Arguments:
        name - name or set of names to identify process, must be unique to process manager.
        """

        if name == []:
            """Start all managed processes."""
            for process in self.processes:
                self.processes[name].execute()
        else:
            for process in name:
                """Start a single process."""
                print('Starting {}'.format(name))
                self.processes[name].execute()

    def stop(self,**name):
        if name == []:
            """Stop all managed processes."""
            print("Shutting down")
            for process in self.processes:
                self.processes[name].popen.kill()
                self.processes[name].popen.wait()
        else:
            for process in name:
                """Stop a process by name."""
                print("Shutting down " + name)
                self.processes[name].popen.kill()
                self.processes[name].popen.wait()




def main():
    """Run a process manager in the foreground."""
    process_names = [["sleep", "python sleeper.py"],
                     ["crash", "python crash.py"]]
    # Once the threading module is working fine, then we can begin connecting the proceses through 0mq.
    with ProcessManager() as manager:
        # Initialize all the processes
        for proc in process_names:
            manager.createProcess(*proc)

        manager.start()

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
