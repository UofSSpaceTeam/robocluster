Wire Protocol Specification
===========================

The following describes the various messages that Robocluster uses,
and how they are formatted.

Most of Robocluster uses JSON serialized data, as it is human readable making
it easy to debug, many programming languages support it, and is very flexible
with you you can structure you data.

Every transmission over the network is reffered to as a "message".
Messages have the following structure in JSON::

    {
        'source': <source>,
        'type': <message type>,
        'data': <nested JSON object>
    }

The 'source' field marks where the message came from. TODO...

The 'data' field varies depending on the message type, and simple contains
the data that the virtual device is sending.

There are several message types:

- heartbeat
- publish
- send
- request
- reply

TODO...
