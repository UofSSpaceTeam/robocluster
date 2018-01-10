class Port:
    """Provides a high level wrapper for arbitrary hardware protocols"""

    #TODO: Define a good way to standardize __init__ while also initializing
    #      parameters specific to a Port type (baudrate for serial,
    #      group for multicast, etc).

    async def read(self):
        raise NotImplementedError("Port is an abstract class")

    def write(self, packet):
        raise NotImplementedError("Port is an abstract class")

    async def _send_task(self):
        raise NotImplementedError("Port is an abstract class")

    async def _receive_task(self):
        raise NotImplementedError("Port is an abstract class")

    async def enable(self):
        """
        Starts the receive_task and send_task.
        It is a coroutine in case the interface needs to call
        other asynchronous coroutines during initialization.
        """
        self._loop.create_task(self._send_task())
        self._loop.create_task(self._receive_task())

