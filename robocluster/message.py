class Message:
    """Base message type for network."""

    def __init__(self, type, source, dests, endpoint, data):
        """
        Initialize a message.

        Arguments:
            type: message type (str)
            source: source of message (str)
            dests: destinations of message (list(str))
            type: message type (str)
            data: JSON encodable data.
        """
        self.type = type
        self.source = source
        self.dests = dest
        self.endpoint = endpoint
        self.data = data

    def __iter__(self):
        yield 'type', self.type
        yield 'source', self.source
        yield 'dests', self.dests
        yield 'endpoint', self.endpoint
        yield 'data', self.data

    @classmethod
    def decode(cls, codec, raw):
        try:
            decode = getattr(self, 'from_' + codec)
        except AttributeError:
            err = 'decoder for {}'.format(codec)
            raise NotImplementedError(err)
        return decode(raw)

    def encode(self, codec):
        """Encode the message to bytes."""
        try:
            encode = getattr(self, 'to_' + codec)
        except AttributeError:
            err = 'encoder for {}'.format(codec)
            raise NotImplementedError(err)
        return encode()

    @classmethod
    def from_dict(cls, d):
        return cls(
            d['type'],
            d['source'],
            d['dests'],
            d['endpoint'],
            d['data'],
        )

    def to_dict(self):
        return dict(self)

    @classmethod
    def from_json(cls, raw):
        from json import loads
        return cls.from_dict(loads(raw))

    def to_json(self, source):
        from json import dumps
        return dumps(self.to_dict())

    @classmethod
    def from_msgpack(cls, raw):
        from msgpack import unpackb
        return cls.from_dict(unpackb(raw))

    def to_msgpack(self):
        from msgpack import packb
        return packb(self.to_dict())

    def __repr__(self):
        return '{}({!r}, {!r}, {!r}, {!r}, {!r})'.format(
            self.__class__.__name__,
            self.type,
            self.source,
            self.dests,
            self.endpoint,
            self.data
        )

