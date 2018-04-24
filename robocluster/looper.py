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

        self._coros = []
        self._tasks = None

    @property
    def loop(self):
        return self._loop

    def create_task(self, coro):
        """Create a task in the event loop."""
        def _create_task():
            self._tasks.append(self.loop.create_task(coro))
        self.loop.call_soon_threadsafe(_create_task)

    def add_daemon_task(self, coro, *args, **kwargs):
        """
        Add a daemon task and starts it if the looper is started.

        Arguments and keyword arguments past coro are passed down to coro when
        it is started.
        """
        self._coros.append((coro, args, kwargs))
        if self._tasks is not None:
            self.create_task(coro(*args, **kwargs))

    def sleep(self, seconds):
        """
        Suspend execution for seconds.

        This method is a coroutine.
        """
        return asyncio.sleep(seconds, loop=self.loop)

    def start(self):
        """Start daemon tasks."""
        if self._tasks is not None:
            return

        self._tasks = []
        for coro, args, kwargs in self._coros:
            self.create_task(self._coro_wrapper(coro, *args, **kwargs))

    async def _coro_wrapper(self, coro, *args, **kwargs):
        while ...:
            try:
                await coro(*args, **kwargs)
            except asyncio.CancelledError:
                raise
            except:  # pylint: disable=W0702
                import traceback
                traceback.print_exc()
                break

    def stop(self):
        """Stop daemon tasks."""
        if self._tasks is None:
            return
        for task in self._tasks:
            task.cancel()
        self._tasks = None

    def __enter__(self):
        """Enter context manager, equivalent to calling start()."""
        self.start()
        return self

    def __exit__(self, *exc):
        """Exit context manager, equivalent to calling stop()."""
        self.stop()
