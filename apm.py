import asyncio.subprocess
import typing
import logging
import signal as sig

log = logging.getLogger()

PIPE = asyncio.subprocess.PIPE
STDOUT = asyncio.subprocess.STDOUT
DEVNULL = asyncio.subprocess.DEVNULL


class ProcessDefinition:
    exclude_keywords = ['exclude_keywords', 'on_exit']
    name = None
    args = None
    _released = False

    def __new__(cls, *more, **kwargs):
        instance = super().__new__(cls)
        instance.__dict__.update({ k: v for k, v in cls.__dict__.items() if not k.startswith('_') })
        return instance

    def __init__(self, *arg_overrides, **overrides):
        super().__init__()
        if len(arg_overrides) > 0:
            self.args = arg_overrides
        self.__dict__.update(overrides)

    def _popen_args(self):
        popen_args = { k: v for k, v in  self.__dict__.items() if not k.startswith('_') and not k in self.exclude_keywords }
        args = popen_args.pop('args', None)
        name = popen_args.pop('name', None)
        if args is None or name is None:
            log.error('Mandatory attribute is None in {}'.format(str(self)))
        return name, args, popen_args

    def __repr__(self):
        return '<{} name={}, args={}>'.format(
            self.__class__.__name__,
            getattr(self, 'name', 'None'),
            getattr(self, 'args', 'None')
        )

    def on_exit(self, returncode: int):
        raise NotImplementedError()

_pids = {}
_pnames = {}
_futures = []
_lock = asyncio.Lock()


async def restart(procdef: ProcessDefinition) -> asyncio.subprocess.Process:
    """
    Restarts/starts a process. If the process is currenlty executing it will be killed then restarted.

    Parameters
    ----------
    procdef : ProcessDefinition
        The processe's definition.

    Returns
    -------
    asyncio.subprocess.Process
        The created asyncio process.
    """
    name, args, popen_args = procdef._popen_args()

    # if the process was released, unrelease it
    procdef._released = False

    # kill the process if it exists
    while name in _pnames:
        kill(procdef)
        await _pnames[name].wait()

    with (await _lock):
        # create the async process, lock is necessary incase two identical procdef's are started at the same time
        if isinstance(args, str):
            process = await asyncio.create_subprocess_shell(args, **popen_args)
        else:
            process = await asyncio.create_subprocess_exec(*args, **popen_args)

        # register the async process in our globals
        _pids[process.pid] = process
        _pnames[name] = process
    return process


async def _run(procdef: ProcessDefinition):
    """
    Run the given process definition until it exists successfully. This function is a coroutine.

    Parameters
    ----------
    procdef: ProcessDefinition
        The processes definition

    Returns
    -------
    int
        The program's return value.
    """
    name, _, _ = procdef._popen_args()

    # check that the process doesn't already exist
    if name in _pnames:
        log.error("Failed to start process('{}') because a process with the same name already exists.")
        return -1

    # start the loop until the process exists successfully
    returncode = None
    process = await restart(procdef)
    while process is not None:
        log.info("Started process({}, '{}')".format(process.pid, name))
        returncode = await process.wait()
        pid = int(process.pid)
        _pids.pop(pid, None)
        _pnames.pop(name, None)
        if procdef._released:
            process = None
        else:
            process = await (getattr(procdef, 'on_exit')(procdef, returncode))
        if process is not None:
            log.warning("Process ({}, '{}') failed, exiting with {}. Restaring process.".format(pid, name, returncode))
        else:
            log.info("Process ({}, {}) exited successfully with {}.".format(pid, name, returncode))
    return returncode


def register(procdef: ProcessDefinition):
    """
    Register a process definition to be executed. The process will being execution shortly after this function is
    called.

    Parameters
    ----------
    procdef: ProcessDefinition
        The process definition instance.
    """
    _futures.append(asyncio.ensure_future(_run(procdef)))


def kill(*procdefs: typing.List[ProcessDefinition], signal=sig.SIGKILL):
    """
    Kill the given processes. Sibling processes can also be killed like this so long as they are configured to restart
    on signal being sent.

    Parameters
    ----------
    *procdefs: list(ProcessDefintion)
        The process definition instances to be killed.
    signal: int
        The signal that will be sent to the processes.

    Notes
    -----
    This function only sends the signals, it does not wait for the processes to finish. Therefore this function may
    return before the process is actually killed.
    """
    for pd in procdefs:
        name, _, _ = pd._popen_args()
        process = _pnames.get(name, None)
        if process is not None:
            process.send_signal(signal)


def term(*procdefs: typing.List[ProcessDefinition], signal=sig.SIGKILL):
    """
    This function is similar to kill however the proces will be permanently terminated regardless of its return value.
    This is done by setting _released in the process defintion.
    """
    for pd in procdefs:
        pd._released = True
    kill(*procdefs, signal)

""""
AMP exit method
Singleton instance of procdef's without name
Improve ProcessDefintion interface
Start processes from strings
"""
