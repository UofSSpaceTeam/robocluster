How Robocluster's internals work
================================

.. note:: TODO: Finish this plz!

There are 4 main components that make up robocluster:

- Device
- Member
- Context
- Looper


Looper is responsible for handling the asyncio event loop of the device.
Context encapsulates an event loop, allowing devices to share event loops.
Member handles all the network interaction.
Device combines Looper, Context, and Member to create a single usable entity.

Looper
------

Context
-------

Member
------

Device
------
