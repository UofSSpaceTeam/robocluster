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
The second parameter is a group name. The group name is used behind the scenes
to select an ip address and port number to bind an `IP Multicast`_ socket.
Devices that have the same group name can talk to each other using the publish
mechanism.

Next we'll create a task that prints "Hello world" and attach it to the device::

    from robocluster import Device

    device = Device('device', 'rover')

    @device.task
    def hello():
        print("Hello world!")

    device.run()

``device.task`` is a decorator function that attaches or registers the
``hello()`` function to be called by the device.
``device.run()`` Starts the device and calls the hello function.
What the run method is doing behind the scenes is it creates an asyncio
event loop and calls the ``run_forever()`` method of the event loop.
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
over the network. You can stop the program with Control-C. It will throw a
KeyboardInterrupt exception which you can avoid by catching the exception like so::

    try:
        device.run()
    except KeyboardInterrupt:
        pass

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

This starts the devices and waits for you to press Control-C. We didn't use
``device.run()`` in this case because the ``run()`` method blocks, and wouldn't
let us start multiple devices. The ``device.start()`` method allows you to start
up a device and continue doing other things while it runs.

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
Currently ``send`` uses TCP to transmit data, in the future we hope to integrate
USB Serial communication with the send function.
Lets create two devices::

    device_a = Device('device_a', 'rover')
    device_b = Device('device_b', 'rover')

Create a callback on device_b for "direct-msg" from any device::

    @device_b.on('*/direct-msg')
    async def callback(event, data):
        print('device_b got message: {}'.format(data))

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

    @deviceA.on('*/request')
    async def reply(event, data):
        await deviceA.reply(event, 1234)

Then set up deviceB to request the data every second::

    @deviceB.every('1s')
    async def get_data():
        data = await deviceB.request('deviceA', 'request')
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


Serial Device Communication
---------------------------

.. note:: The microcontroller side of this will change in the near future.

Now we'll look at how to talk to a serial device with robocluster.
For this you will need an Arduino with the following code on it:

::

    #include <Arduino.h>
    #include <ArduinoJson.h>

    StaticJsonBuffer<200> jsonBuffer;
    JsonObject& root = jsonBuffer.createObject();
    JsonObject& publish = jsonBuffer.createObject();

    void send_message() {
        root.printTo(Serial);
    }

    void send_data() {
        publish.printTo(Serial);
    }

    void setup() {
        pinMode(13, OUTPUT);
        Serial.begin(115200);
        root["type"] = "heartbeat";
        root["source"] = "Teensy1";
        JsonObject& nested = root.createNestedObject("data");
        nested["key1"] = 42;
        root["data"] = nested;

        publish["type"] = "publish";
        publish["source"] = "Teensy1";
        JsonObject& pub_nested = publish.createNestedObject("data");
        pub_nested["topic"] = "Teensy1/sensor1";
        pub_nested["data"] = 77.4;
        publish["data"] = pub_nested;

    }

    void loop() {
        send_message();
        digitalWrite(13, HIGH);
        delay(500);
        send_data();
        delay(500);
        if(Serial.available() > 1){
            digitalWrite(13, LOW);
            while(Serial.available()) {
                Serial.read();
            }
            delay(500);
        }
    }

This sends a heartbeat every second, and if a message is sent to the Arduino,
it will sleep for half a second so you can confirm the Arduino received the message.
It also publishes the topic ``sensor`` every second.

Once this is flashed
to your Arduino, lets create a device on the python side and set up the serial port::

    from robocluster import SerialDriver, Device

    serialDevice = SerialDriver('/dev/ttyACM0', 'rover')
    tester = Device('tester', 'rover')

``SerialDriver`` is a special type of virtual device that represents a physical serial
device on the robocluster network. You initialize it with a path to a serial port
on Posix systems, or a COM port on Windows, and when SerialDriver receives a heartbeat
message from the physical device, it will update its name to match the physical device.
It then behaves like a bridge between the robocluster network and the serial device.
We created the ``tester`` Device to interact with the serial device.

Lets make the ``tester`` virtual device publish some data to the network::

    @tester.every('1s')
    async def publish_data():
        await tester.publish('testThings', 27)

And also have it subscribe to the 'sensor1' data the Arduino is publishing::

    @tester.on('*/sensor1')
    def print_sensor(event, data):
        print('Sensor 1 data: {}'.format(data))

Finally, add::

    try:
        serialDevice.start()
        tester.start()
        serialDevice.wait()
        tester.wait()
    except KeyboardInterrupt:
        serialDevice.stop()
        tester.stop()

and run the script. You should see the event and data from the microcontroller
printed to the console about every 1.5 seconds, and the led on pin 13 of the
Arduino should blink at the same rate.


.. _IP Multicast: https://en.wikipedia.org/wiki/IP_multicast
.. _Python asyncio home: https://docs.python.org/3/library/asyncio.html
.. _Python Tasks and coroutines: https://docs.python.org/3/library/asyncio-task.html
.. _JSON: https://json.org/
