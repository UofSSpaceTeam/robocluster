# THIS FILE IS SUBJECT TO THE LICENSE TERMS GRANTED BY THE UNIVERSITY OF SASKATCHEWAN SPACE TEAM (USST).

import time
import sys
from subprocess import Popen
import shlex


class RoboProcess:
    """
    This class contains the layout and metadata of a process.
    """
    def __init__(self, cmd):
        """
        This method creates a process containing command cmd.
        """
        self.cmd = cmd
        self.popen = None

    def execute(self):
        """
        This method creates a Popen object and turns the command into an argument
        that the Popen object can use.
        """
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
        """Initializes the process manager"""
        # process dictionary stores RoboProcess instances indexed
        # by the process name
        self.process_dict = {}

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, *exc):
        """Exit context manager, makes sure all processes are stopped."""
        self.stopAllProcesses()
        return False

    def isEmpty(self):
        """
        Confirms whether process_dict is empty.
        """
        if self.process_dict == {}:
            return True
        else:
            return False

    def createProcess(self, name, command):
        """
        Creates a process.
        Checks if command is type string if so it returns True otherwise it returns False.
        Checks if name has not been used otherwise informs that name is taken.
        """

        if isinstance(command, str):
            if name in self.process_dict:
                print("Name already taken.")
            else:
                print("Created {}".format(name))
                self.process_dict[name] = RoboProcess(command)
            return True
        else:
            return False

    def createThread(self): # TODO: Do we really need this if we have createProcess?
        """
        TODO create a function that takes in parameters and uses those parameters to
        ceate one single thread. The thread must then be stored in "self.T".
        """
        pass

    def startProcess(self, name):
        """
        Starts a single process.
        """
        print('Starting {}'.format(name))
        self.process_dict[name].execute()

    def startAllProcesses(self):
        """
        Starts all processes in process_dict.
        """

        for process in self.process_dict:
            self.startProcess(process)

    def stopProcess(self, name):
        """
        Stops a specific process in process_dict.
        """

        print ("Shutting down " + name)
        self.process_dict[name].popen.kill()
        self.process_dict[name].popen.wait()

    def stopAllProcesses(self):
        """
        Stops all processes in process_dict.
        """

        print ("Shutting down")

        for process in self.process_dict:
            self.stopProcess(process)

    def status(self, thread):
        """
        TODO: Return the status of a thread or process
        """
        raise NotImplementedError()

    def verify(self, thread):
        """
        TODO: Check the status of the thread or process and perform certain functions based on its status.
        """
        raise NotImplementedError()

    def fix(self, thread):
        """
        TODO: Fix a thread or process if its not running properly.
        """
        raise NotImplementedError()

process_names = [["sleep", "python sleeper.py"],
                 ["crash", "python crash.py"]]
# Once the threading module is working fine, then we can begin connecting the proceses through 0mq.
if __name__ == "__main__":
    with ProcessManager() as manager:
        # Initialize all the processes
        for proc in process_names:
            manager.createProcess(*proc)

        manager.startAllProcesses()

        try:
            while True: # Execute the processes.
                # TODO Run the processes as they should.
                for task in manager.process_dict: # Verify tasks.
                    # taskMgr.verify(task.name)
                    pass
                time.sleep(3)
        except KeyboardInterrupt:
            pass
    sys.exit(0)
