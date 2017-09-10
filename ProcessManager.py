# File ProcessManager.py
#
# THIS FILE IS SUBJECT TO THE LICENSE TERMS GRANTED BY THE UNIVERSITY OF SASKATCHEWAN SPACE TEAM (USST).

import time
import sys
from subprocess import Popen


class RoboProcesses:

    def __init__(self, cmd):
        self.cmd = cmd
        self.popen = None

    def execute(self):
        self.popen = Popen(self.cmd)


class ProcessManager:
    """
    Class: ProcessManager

    This class represents the pocessing module for the robocluster operating system.
    """

    def __init__(self, **kwargs):
        """Initializes the process manager"""
        self.process_dict = {} # Process dictionary: stores all processes

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
        if type(command) == str:
            if name in self.process_dict:
                print("Name already taken.")
            else:
                print("Created {}".format(name))
                self.process_dict[name] = RoboProcesses(command)
            return True
        else:
            return False

    def createThread(self):
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
            self.process_dict[process].popen.kill()
            self.process_dict[process].popen.wait()

    def status(self, thread):
        """
        TODO: Return the status of a thread or process
        """
        if self.isEmpty():
            return None
        else:
            None

    def verify(self, thread):
        """
        TODO: Check the status of the thread or process and perform certain functions based on its status.
        """
        pass

    def fix(self, thread):
        """
        TODO: Fix a thread or process if its not running properly.
        """
        pass

process_names = [["sleep", "python sleeper.py"],
                 ["crash", "python crash.py"]]
# Once the threading module is working fine, then we can begin connecting the proceses through 0mq.
if __name__ == "__main__":
    taskMgr = ProcessManager()
    # Initialize all the processes
    for proc in process_names:
        taskMgr.createProcess(*proc)

    taskMgr.startAllProcesses()

    try:
        while True: # Execute the processes.
            """
            TODO Run the processes as they should.
            """
            for task in taskMgr.process_dict: # Verify tasks.
                # taskMgr.verify(task.name)
                pass
            time.sleep(3)
    except KeyboardInterrupt:
        taskMgr.stopAllProcesses()
        sys.exit(0)
