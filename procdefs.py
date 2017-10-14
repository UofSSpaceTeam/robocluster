import apm
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

class CrashPeriodically(apm.ProcessDefinition):
    args = ['python', 'examples/processes/crash_periodically.py', '2', '12']
    stdout = apm.PIPE
    stderr = apm.DEVNULL
    stdin = apm.DEVNULL

    def on_exit(self, returncode: int):
        if returncode == 0:
            return apm.release(self)
        else:
            return apm.restart(self)

class PrintPeriodically(CrashPeriodically):
    args = ['python', 'examples/processes/print_periodically.py', '3', '30']

import sys

class Bash(apm.ProcessDefinition):
    args = 'bash'
    executable = '/bin/bash'
    stdout = sys.stdout
    stdin = sys.stdin

    def on_exit(self, returncode: int):
        return apm.release(self)

processes = [
    PrintPeriodically(name='pp'),
    Bash(name='bash'),
    CrashPeriodically(name='cp'),
]

for proc in processes:
    apm.register(proc)



loop = asyncio.get_event_loop()
loop.run_forever()