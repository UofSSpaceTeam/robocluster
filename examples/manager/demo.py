'''Example of a files that configures the processes and runs them'''
from robocluster.manager.ProcessManager import ProcessManager, RunOnce
import time

PATH = './demo'

process_list = [
    RunOnce("random-stream", 'python3 {}/random_stream.py'.format(PATH)),
    RunOnce("printer", 'python3 {}/printer.py'.format(PATH)),
    # RunOnce("serialtest", f'python {PATH}/serial_test.py'),
]


with ProcessManager() as manager:
    # Initialize all the processes
    for proc in process_list:
        manager.addProcess(proc)

    # Start all processes
    manager.start()

    try:
        # Run asyncio event loop
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass # exit cleanly
