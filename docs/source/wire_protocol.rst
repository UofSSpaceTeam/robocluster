Wire Protocol Specification
===========================

.. warning:: This is now out of date, will update soon.

The following describes the various messages that Robocluster uses,
and how they are formatted.

Most of Robocluster uses JSON serialized data, as it is human readable making
it easy to debug, many programming languages support it, and is very flexible
with you you can structure you data.

Every transmission over the network is reffered to as a "message".
Messages have the following structure in JSON::

    {
        'source': <source>,
        'type': <message_type>,
        'data': <nested_JSON_object>
    }

The 'source' field marks where the message came from. It is a unique identifier
for the socket that sent it, and is not very useful to humans.

The 'data' field varies depending on the message type, and simple contains
the data that the virtual device is sending.

There are several message types:

- heartbeat
- publish
- send
- request
- reply

.. note:: TODO: I saw a 'connect' message being used in router.py?

``publish`` and ``heartbeat`` messages are typically done over UDP Multicast/Broadcast,
``send``, ``request``, and ``reply`` messages are typically done over TCP connections.

heartbeat
---------
Virtual devices are constantly publishing heartbeat messages, currently
every 100ms, though this can be changed. Heartbeat messages let virtual
devices on the network know of each other's existance, as well as some information
about how to connect to each other. The JSON structure of a heartbeat message is::

    {
        'source': <source>,
        'type': 'heartbeat',
        'data': {
            'source': <source?>,
            'listen': <port_number>
        }
    }

The listen field tells other vitual devices which port number to connect to in
order to ``send`` or ``request`` with that virtual device.

The 'source' field within the 'data' field contains the name of the device.

publish
-------
Publish messages are broadcasted to every virtual device on the network.
The JSON structure is as follows::

    {
        'source': <source>,
        'type': 'publish',
        'data': {
            'topic': <device_name>'/'<topic_name>,
            'data': <nested_JSON_object>
        }
    }

The 'topic' field is used to label a message so that publishes can be distinguished
from each other. On the receiving end, a virtual device can subscribe to a topic,
so that a function can be called when ever that topic is published by another device.
When you ask a virtual device to publish a particular topic, the device will prepend
its own name to the desired topic name, separated with a ``'/'``. This lets other virtual
devices subscribe to topics emitted from a specific device, or subscribe to every
topic published from that virtual device. If you want to subscribe to a topic and
don't care who publishes it, you can use ``*/topic_name``.

The 'data' field is just whatever data you want to publish, sensor values, commands, etc.
