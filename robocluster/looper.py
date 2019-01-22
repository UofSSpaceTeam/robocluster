import asyncio


class Looper:
    """
    A wrapper for an event loop that allows for a group of daemon tasks.

    The daemon tasks can all be started and stopped.
    """

    def __init__(self, loop=None):
        """
        Initialize the looper.

        When loop is omitted, the current event loop is used.
        """
        self._loop = loop or asyncio.get_event_loop()
        if not isinstance(self._loop, asyncio.AbstractEventLoop):
            raise TypeError

        self._daemons = []
        self._tasks = []
        self._running_tasks = None

    @property
    def loop(self):
        return self._loop

    def create_task(self, coro, *args, **kwargs):
        """Create a task in the event loop."""
        if self._running_tasks is None:
            self._tasks.append((coro, args, kwargs))
            return
        self._create_task(self._coro_wrapper(coro, *args, **kwargs))

    def _create_task(self, coro):
        def _create_task():
            self._running_tasks.append(self.loop.create_task(coro))
            # self.loop.create_task(coro) calls asyncio's "create_task"
        self.loop.call_soon_threadsafe(_create_task)

    def create_daemon(self, coro, *args, **kwargs):
        """
        Add a daemon task and starts it if the looper is started.

        Arguments and keyword arguments past coro are passed down to coro when
        it is started.
        """
        # TODO: make this a class level decorator?
        self._daemons.append((coro, args, kwargs))
        if self._running_tasks is not None:
            self._create_task(self._daemon_wrapper(coro, *args, *kwargs))

    def sleep(self, seconds):
        """
        Suspend execution for seconds.

        This method is a coroutine.
        """
        return asyncio.sleep(seconds, loop=self.loop)

    def start(self):
        """Start daemon tasks."""
        if self._running_tasks is not None:
            return

        self._running_tasks = []
        for coro, args, kwargs in self._daemons:
            self._create_task(self._daemon_wrapper(coro, *args, **kwargs))

        for coro, args, kwargs in self._tasks:
            self._create_task(self._coro_wrapper(coro, *args, **kwargs))
        self._tasks = []

    async def _coro_wrapper(self, coro, *args, **kwargs):
        try:
            await coro(*args, **kwargs)
        except asyncio.CancelledError:
            raise
        except:  # pylint: disable=W0702
            import traceback
            traceback.print_exc()

    async def _daemon_wrapper(self, coro, *args, **kwargs):
        while ...:
            try:
                await coro(*args, **kwargs)
                print('daemon exited', coro)
            except asyncio.CancelledError:
                raise
            except:  # pylint: disable=W0702
                import traceback
                traceback.print_exc()

    def stop(self):
        """Stop daemon tasks."""
        if self._running_tasks is None:
            return
        for task in self._running_tasks:
            task.cancel()
        self._running_tasks = None

    def __enter__(self):
        """Enter context manager, equivalent to calling start()."""
        self.start()
        return self

    def __exit__(self, *exc):
        """Exit context manager, equivalent to calling stop()."""
        self.stop()
