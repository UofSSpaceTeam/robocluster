"""Message passing for robocluster."""

from collections import defaultdict

from .net import Link, MulticastReceiver


class Device:
    """A device to interact with the robocluster network."""

    def __init__(self, name, address):
        self.name = name

        self.link = Link(*address)
        self.subscriber = MulticastReceiver(*address)

        self.events = defaultdict(list)

    def publish(self, topic, data):
        """Publish to topic."""
        packet = {
            'event': '{}/{}'.format(self.name, topic),
            'data': data,
        }
        self.link.send(packet)

    def on(self, event):
        """Add a handler to an event."""
        def adder(handler):
            """Add a handler to an event."""
            self.events[event].append(handler)
            return handler
        return adder

    def run(self):
        """Run the device."""
        try:
            while True:
                packet, _ = self.subscriber.recieve()
                if not packet:
                    continue
                event = packet['event']
                if event in self.events:
                    for handler in self.events[event]:
                        handler(packet['data'])
        except KeyboardInterrupt:
            pass
        finally:
            self.link.close()
            self.subscriber.close()
