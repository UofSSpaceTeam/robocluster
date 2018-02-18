import json


class Message:
    """Base message type for network."""

    def __init__(self, source, type, data):
        """
        Initialize a message.

        Arguments:
            source: source of message (str)
            type: message type (str)
            data: JSON encodable data.
        """
        self.source = source
        self.type = type
        self.data = data

    @classmethod
    def from_bytes(cls, msg, encoding='json'):
        """Create a Message from bytes."""
        try:
            return cls.from_string(msg.decode())
        except UnicodeDecodeError:
            raise ValueError('Invalid utf-8.')

    @classmethod
    def from_string(cls, msg):
        """Create a Message from a utf-8 string."""
        try:
            packet = json.loads(msg)
        except json.JSONDecodeError:
            raise ValueError('Invalid JSON.')

        if any(k not in packet for k in ('source', 'type', 'data')):
            raise ValueError('Improperly formatted message.')

        return cls(packet['source'], packet['type'], packet['data'])

    def encode(self):
        """Encode the message to bytes."""
        return self.to_json().encode()

    def to_json(self):
        return json.dumps({
            'source': self.source,
            'type': self.type,
            'data': self.data,
        })

    def __repr__(self):
        return '{}({!r}, {!r}, {!r})'.format(
            self.__class__.__name__,
            self.source,
            self.type,
            self.data
        )

