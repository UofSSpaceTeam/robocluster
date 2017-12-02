import random

from robocluster.util import duration_to_seconds

def test_duration_to_seconds():
    # test that integers are unchanged
    rnd_integer = random.randint(-10000, 10000)
    assert(duration_to_seconds(rnd_integer) == rnd_integer)
    # test that floats are unchanged
    rnd_float = random.random()
    assert(duration_to_seconds(rnd_float) == rnd_float)

    # test minute values
    time_string = '1 m'
    assert(duration_to_seconds(time_string) == 60)
    time_string = '1 minute'
    assert(duration_to_seconds(time_string) == 60)
    time_string = '2 minutes'
    assert(duration_to_seconds(time_string) == 120)

    # test second values
    time_string = '1 s'
    assert(duration_to_seconds(time_string) == 1)
    time_string = '1 second'
    assert(duration_to_seconds(time_string) == 1)
    time_string = '2 seconds'
    assert(duration_to_seconds(time_string) == 2)

    # test millisecond values
    time_string = '1 ms'
    assert(duration_to_seconds(time_string) == 0.001)
    time_string = '1 millisecond'
    assert(duration_to_seconds(time_string) == 0.001)
    time_string = '2 milliseconds'
    assert(duration_to_seconds(time_string) == 0.002)

    # test invalid input
    assert(duration_to_seconds('invalid') == -1)
    assert(duration_to_seconds('1 ps') == -1)

