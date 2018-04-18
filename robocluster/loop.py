import asyncio
import contextlib
from abc import ABC, abstractmethod
from concurrent.futures import Future
from threading import Thread


class LoopThread(Thread):
    """A class that runs an event loop in a separate thread."""

    def __init__(self, name=None, loop=None, cancel_remaining_tasks=True):
        """
        Construct a thread responsible for running an asyncio event loop.

        Arguments are:
        *name* is the thread name. As per threading.Thread.

        *loop* is the event loop to run. By default this is created as per
        asyncio.new_event_loop().

        *cancel_remaining_tasks* is a boolean that states whether to cancel
        unfinished tasks in the event loop on stop.
        """
        super().__init__(name=name)
        self.loop = loop if loop else asyncio.new_event_loop()
        self.cancel_remaining_tasks = cancel_remaining_tasks

    def run(self):
        """Run the event loop."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

        if not self.cancel_remaining_tasks:
            return

        for task in asyncio.Task.all_tasks(loop=self.loop):
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                self.loop.run_until_complete(task)

    def create_task(self, coro):
        """
        Create a task in the event loop from the given coroutine.
        """
        loop = asyncio.get_event_loop()
        if loop is self.loop:
            return loop.create_task(coro)

        if not self.loop.is_running():
            msg = 'Event loop must be running to create from different thread.'
            raise RuntimeError(msg)

        future = Future()
        def _create_task():
            task = self.loop.create_task(coro)
            future.set_result(task)
        self.loop.call_soon_threadsafe(_create_task)
        # blocks until task has been created by the loop
        return future.result()

    def cancel_task(self, task):
        """Cancel a task in the event loop."""
        self.loop.call_soon_threadsafe(task.cancel)

    def stop(self):
        """Stop event loop and thread."""
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.join()


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
        self._coros = []
        self._tasks = None

    @property
    def loop(self):
        return self._loop

    def create_task(self, coro):
        """Create a task in the event loop."""
        return self.loop.create_task(coro)

    def add_daemon_task(self, coro, *args, **kwargs):
        """
        Add a daemon task and starts it if the looper is started.

        Arguments and keyword arguments past coro are passed down to coro when
        it is started.
        """
        self._coros.append((coro, args, kwargs))
        if self._tasks is not None:
            task = self.create_task(coro(*args, **kwargs))
            self._tasks.append(task)

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
            task = self.create_task(self._coro_wrapper(coro, *args, **kwargs))
            self._tasks.append(task)

    async def _coro_wrapper(self, coro, *args, **kwargs):
        while ...:
            try:
                await coro(*args, **kwargs)
            except asyncio.CancelledError:
                raise
            except:
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
