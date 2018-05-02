Usage Tutorial
==============


At the core of robocluster is the concept of a "device".
If you are familiar with embedded systems, you can think of a device as a
virtual microcontroller running a real time operating system.
A device abstracts the act of communicating with other devices and managing
tasks that run periodically. Using robocluster generally consists of
creating some devices and attaching some callback functions and tasks to them
and then running the devices to let them do their work.

Basic Device Creation
---------------------

Lets create a device::

    from robocluster import Device

    device = Device('device', 'rover')

The first parameter to the Device constructor is the name that you want to
assign to the device. This name identifies the device on the network.
The second parameter is a group name.
Devices that have the same group name can talk to each other using the publish
mechanism.

Sometimes you will need to specify the ``network`` parameter like so::

    device = Device('device', 'rover', network='10.0.0.0/24')

This gives the Device the information it needs to figure out the IP Broadcast address
to publish to. In this case "10.0.0.0" is the network address, and "/24" is the subnet mask.

Next we'll create a task that prints "Hello world" and attach it to the device::

    from robocluster import Device

    device = Device('device', 'rover')

    @device.task
    def hello():
        print("Hello world!")

    device.start()
    device.wait()

``device.task`` is a decorator function that attaches or registers the
``hello()`` function to be called by the device.
``device.start()`` Starts the asycio event loop for the device which runs ``hello``.
``device.wait()`` Blocks until the device exits (which is indefinite unless and exception is thrown).
The point of robocluster devices is to handle most of the details of the python
asyncio library, but if you are new to asyncio I would recommend learning
it as the tasks and callbacks we write in the near future will use some asyncio
syntax and assume that you know what the ``await`` keyword is doing. Here are
some resources on asyncio:

`Python asyncio home`_: This is the table of contents for all the asyncio
information. Don't read the whole thing unless you want to as there is a lot of
information, some of it assuming intermediate to advanced knowledge of Python.

`Python Tasks and coroutines`_: This has some examples of coroutines work, and
is a pretty good explanation of how write and use basic coroutines.

If you google stuff on asyncio, you'll find a lot of people talking about how
confusing asyncio is, so if you don't understand the official documentation,
that's normal :). I've found that in practice asyncio isn't all that
difficult to use if you don't think about the details of the event loop and
generators and what not.

Back to our example, if you run this python code it should print "Hello world"
and just sit there doing nothing. Devices run forever in the foreground by
default because most of the time you will want them to react events triggered
over the network. You can stop the program with Control-C.

Lets make this a tiny bit more interesting by changing the ``hello()`` function
to run every second. Change the function definition to this::

    @device.every('1s')
    def hello():
        print("Hello world!")

Now the device will call print "Hello world!" every second. The
``device.every()`` decorator takes a few different parameters described in
:func:`robocluster.util.duration_to_seconds`.

Multiple Devices
----------------

Lets start a new example that involves multiple devices. We'll create a program
where one device publishes "Hello {}" to the network, and another device
receives this message and fills in its own name and prints it to the console.

::

    from robocluster import Device

    deviceA = Device('deviceA', 'rover')
    deviceB = Device('deviceB', 'rover')

This just creates two devices.

::

    @deviceA.every('1s')
    async def send_message():
        await deviceA.publish('Greeting', 'Hello {}')

This creates a task for deviceA that runs every second which we have seen
before. The body of the function publishes the message/event to the network.
Device.publish is a coroutine, so you need to use the ``await`` keyword on it.
When ``send_message`` calls that line it will let other functions run while it
waits for ``deviceA.publish(..)`` to finish. If you don't use ``await``,
``send_message`` will finish before ``deviceA.publish`` can run, and nothing
will happen. The ``async`` keyword on the function definition is required to use
the ``await`` keyword, just part of Python 3.5+ syntax rules.

Messages that are published in robocluster have two main components, event and
data. The event in this case is "Greeting", and is just a tag to identify the
message by. The data in this case is "Hello {}". The data can be almost whatever
you want, as long as it can be encoded. By default devices encode data in `JSON`_
format, so if you stick to strings, numbers, lists and dictionaries, you
shouldn't run into problems. Robocluster does support formats other than JSON
which we may cover later.

::

    @deviceB.on('deviceA/Greeting')
    async def print_greeting(event, data):
        print(data.format(deviceB.name))

This sets up deviceB to call the print_greeting function when ever deviceA
publishes the "Greeting" message. If we wanted to listen for the "Greeting"
message from any device, we could use ``@deviceB.on('*/Greeting')``.
The ``on`` decorator supports unix filename globbing syntax.

The ``print_greeting()`` function takes two arguments, event and data.
These are the event and data that deviceB sent, but note that on the receiving
end, event has the name of the sending device prepended. This is useful if you
use wild cards such as ``'*/Greeting'`` and want to do different things depending
on who the sender was. When deviceA published the "Greeting" message,
robocluster automatically prepended the device name to "Greeting".

::

    try:
        deviceA.start()
        deviceB.start()
        deviceA.wait()
        deviceB.wait()
    except KeyboardInterrupt:
        deviceA.stop()
        deviceB.stop()

This starts the devices and waits for you to press Control-C.
You should see "Hello deviceB" printed to the console every second when you run
this code.

As an exercise to check that you understand how to do this message passing thing,
change deviceB to publish the modified string it got from deviceA, and create a
new deviceC that does the printing of the final message to the console.
Then modify deviceA to randomly choose between "Hello {}" and "Goodbye {}".

Sending Data Directly
---------------------

For messages that contain a lot of data or are sent at a high frequency,
it is probably not a good idea to broadcast that to every device on the network.
In this case it is more useful to send the message directly to the target device.
Currently ``send`` uses TCP to transmit data.
Lets create two devices::

    device_a = Device('device_a', 'rover')
    device_b = Device('device_b', 'rover')

Create a callback on device_b for "direct-msg" from any device::

    @device_b.on('direct-msg')
    async def callback(event, data):
        print('device_b got message: {}'.format(data))

Note that this uses the same ``.on`` method as subscribe, but the topic
does not contain a "/" character. It's a bit of a subtle distinction, but this
is what differentiates send and subscribe, subscribe contains a "/" character in
the topic name and send doesn't. The idea is that send is just like listening on
a socket; you have no idea who will connect and send you information, and for the
most part you don't care. When subscribing on the other hand, you may want finer
control over who is publishing the topic.

Create a periodic task for device_a that sends a number to device_b::

    @device_a.every('1s')
    async def transmit():
        await device_a.send('device_b', 'direct-msg', 1234)

And start the devices::

    try:
        device_a.start()
        device_b.start()
        device_a.wait()
        device_b.wait()
    except KeyboardInterrupt:
        device_a.stop()
        device_b.stop()

The ``device.send()`` method takes 3 parameters, the first is the name
of the device that you are sending to, the second is a data identifier
just like the publish method, and the third parameter is the data its self.

Request Data from a device
---------------------------

You can also request data directly from another device.

Lets create two devices::

    deviceA = Device('deviceA', 'rover')
    deviceB = Device('deviceB', 'rover')

And set up deviceA to reply to the "request" event with some data::

    @deviceA.on_request('request')
    async def reply(val):
        return val*2

Then set up deviceB to request the data every second::

    @deviceB.every('1s')
    async def get_data():
        data = await deviceB.request('deviceA', 'request', 1234)
        print(data)

And finally run the devices::

    try:
        deviceA.start()
        deviceB.start()
        deviceA.wait()
        deviceB.wait()
    except KeyboardInterrupt:
        deviceA.stop()
        deviceB.stop()

This is not just a request for data, but more of a remote procedure call mechanism.
Your reply function can take any amount of parameters including keyword arguments.
Whatever your function returns must be JSON serializeable.


.. _Python asyncio home: https://docs.python.org/3/library/asyncio.html
.. _Python Tasks and coroutines: https://docs.python.org/3/library/asyncio-task.html
.. _JSON: https://json.org/
