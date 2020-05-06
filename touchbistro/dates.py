"""Common functions and definitions for date handling"""
from datetime import datetime
from lib7shifts.dates import get_local_tz

#: The amount of seconds to ADD to a Cocoa timestamp to arrive at Unix Epoch
UNIX_COCOA_OFFSET = 978307200.0


def unixepoch_2_cocoa(unixepochtime):
    "Given a Posix timestamp, return a Cocoa epoch timestamp"
    return unixepochtime - UNIX_COCOA_OFFSET


def cocoa_2_unixepoch(cocoatime):
    "Given a Cocoa timestamp, return the Unix Epoch version"
    return cocoatime + UNIX_COCOA_OFFSET


def cocoa_2_datetime(cocoatime):
    "Returns a localized Datetime object corresponding to the cocoa time"
    return datetime.fromtimestamp(cocoa_2_unixepoch(cocoatime)).replace(
        tzinfo=get_local_tz()
    )


def datetime_2_cocoa(datetime_obj):
    "Returns a cocoa epoch timestamp from a datetime object"
    return unixepoch_2_cocoa(datetime_obj.timestamp())
