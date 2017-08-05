from subprocess import Popen
import time
import signal
import sys


command_list = [['python', 'sleeper.py'],
                ['python', 'crash.py']]

# subprocesses ignore SIGINT
signal.signal(signal.SIGINT, signal.SIG_IGN)

# start processes
processes = []
for cmd in command_list:
    processes.append(Popen(cmd))


def sigint_hander(a, b):
    ''' Shut down all subprocesses when the manager is killed'''
    print('Shutting down')
    for proc in processes:
        proc.kill()
        proc.wait()
        print(f'Program: {proc.args}\t exit: {proc.returncode}')
        sys.exit(0)

signal.signal(signal.SIGINT, sigint_hander)
while True:
    for proc in processes:
        return_code = proc.poll()
        if return_code is not None:
            # Restart the process
            print("Disabling interupts")
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            print("restarting proc")
            processes.append(Popen(proc.args))
            print("removing stale proc")
            processes.remove(proc)
            print("Re-enabling interupts")
            signal.signal(signal.SIGINT, sigint_hander)
    time.sleep(0.1)

