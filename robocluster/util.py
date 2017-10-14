"""Utility functions for robocluster."""

import re


def duration_to_seconds(duration):
    """
    Convert duration as a string to seconds if needed.

    Args:
        duration (str, float): time in seconds or as text.

    Returns:
        int: seconds in duration, or -1 if duration is invalid.

    Supported units:
        - 'm', 'minute', 'minutes': 60 seconds
        - 's', 'second', 'seconds': 1 seconds
        - 'ms', 'millisecond', 'milliseconds': 0.001 seconds
    """
    if isinstance(duration, int) or isinstance(duration, float):
        return duration

    value = -1.0
    units = {
        'm': 60, 'minute': 60, 'minutes': 60,
        's': 1, 'second': 1, 'seconds': 1,
        'ms': 0.001, 'millisecond': 0.001, 'milliseconds': 0.001,
    }

    match = re.match(r'^(\d+)\s*(\w+)$', duration)
    if match:
        duration, unit = match.groups()
        try:
            value = float(duration) * units[unit]
        except KeyError:
            pass

    return value
