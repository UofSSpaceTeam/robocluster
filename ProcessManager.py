"""THIS FILE IS SUBJECT TO THE LICENSE TERMS GRANTED BY THE UNIVERSITY OF SASKATCHEWAN SPACE TEAM (USST)."""

import shlex
import sys
import asyncio
import logging
from subprocess import Popen
from time import sleep

from robocluster import Device

log = logging.getLogger("Process-Manager")
log.setLevel(logging.INFO)

class RoboProcess:
    """Manages and keeps track of a process."""

    def __init__(self, name, cmd):
        """Initialize a process containing command cmd."""
        if not isinstance(cmd, str):
            raise ValueError('command must be a string')
        self.name = name
        self.cmd = cmd
        self.pid = None
        self.released = False
        self.process = None

    async def restart(self):
        """
        Restarts/starts a process. If the process is currenlty executing it will be killed then restarted.

        Returns
        -------
        asyncio.subprocess.Process
            The created asyncio process.
        """

        # if the process was released, unrelease it
        self._released = False

        # kill the process if it exists
        await self.kill()

        self.process = await asyncio.create_subprocess_shell(self.cmd)

        self.pid = self.process.pid
        return self.process

    async def run(self):
        """
        Run the given process definition until it exists successfully. This function is a coroutine.

        Returns
        -------
        int
            The program's return value.
        """
        # start the loop until the process exists successfully
        returncode = None
        self.process = await self.restart()
        while self.process:
            log.info("Started process({}, '{}')".format(self.pid, self.name))
            returncode = await self.process.wait()
            last_pid = self.pid
            self.pid = None
            if self._released:
                self.process = None
            else:
                self.on_exit(returncode)
            if self.process:
                log.warning("Process ({}, '{}') failed, exiting with {}. Restaring process.".format(last_pid, self.name, returncode))
            else:
                log.info("Process ({}, {}) exited successfully with {}.".format(last_pid, self.name, returncode))
        return returncode

    async def kill(self, timeout=1, release=False):
        """
        Stop the process.

        Ignored if the process is not running.
        """
        if self.process:
            self.process.terminate()
            try:
                future = self.process.wait()
                await asyncio.wait_for(future, timeout)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            self.released = release

    def on_exit(self, returncode):
        """To be called when the process exits"""
        raise NotImplementedError('RoboProcess does not define a default behaivior on exit. Please inherit and define the on_exit(returncode) method')

class RunOnce(RoboProcess):
    """Process that runs """
    def on_exit(self, returncode):
        self.process = None

class RestartOnCrash(RoboProcess):
    """Process that restarts on non zero exit"""
    def on_exit(self, returncode):
        if returncode != 0:
            self.restart()
        else:
            self.process = None


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
        self._futures = []
        self.remote_api_device = Device('remote-api', 'Manager')

        @self.remote_api_device.on('*/createProcess')
        async def remote_createProcess(event, data):
            print('got remote createProcess')
            name = data['name']
            command = data['command']
            self.createProcess(name, command)
            self.start(name)

        @self.remote_api_device.on('*/stop')
        async def remote_stop(event, data):
            print('Got remote stop')
            self.stop()

        @self.remote_api_device.task
        async def rem_print_started():
            print('remote api running')

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, *exc):
        """Exit context manager, makes sure all processes are stopped."""
        self.stop()
        self.remote_api_device.stop()
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
        self.addProcess(RoboProcess(name, command))

    def addProcess(self, roboprocess):
        """Adds roboprocess that was created externally to the manager"""
        if roboprocess.name in self.processes:
            raise ValueError('Process with the same name exists: {name}')
        self.processes[roboprocess.name] = roboprocess


    def start(self, *names):
        """
        Start processes.

        If no arguments are provided, starts all processes.
        """
        processes = names if names else self.processes.keys()
        for process in processes:
            try:
                print('Starting:', process)
                self._futures.append(asyncio.ensure_future(
                    self.processes[process].run()))
            except KeyError:
                pass

    def stop(self, *names, timeout=0):
        """
        Stop processes.

        If no arguments are provided, stops all processes.
        """
        processes = names if names else self.processes.keys()
        for process in processes:
            try:
                print('Stopping:', process)
                asyncio.run_coroutine_threadsafe(
                        self.processes[process].kill(timeout=timeout, release=True),
                        self.loop)
            except KeyError:
                pass

    def run(self):
        """Run the event loop"""
        self.remote_api_device.start()
        self.loop = asyncio.get_event_loop()
        self.loop.run_forever()


def main():
    """Run a process manager in the foreground."""
    process_list = [
        RunOnce('sleep', 'python sleeper.py'),
        RunOnce("printer", "python ./examples/processes/print_periodically.py 1 4"),
        # RestartOnCrash('crasher', 'python crash.py')
    ]

    with ProcessManager() as manager:
        """Initialize all the processes"""
        for proc in process_list:
            manager.addProcess(proc)

        manager.start()

        try:
            manager.run()
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    exit(main())
