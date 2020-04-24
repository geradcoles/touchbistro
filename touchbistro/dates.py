"""Common functions and definitions for date handling"""


def unixepoch_2_cocoa(unixepochtime):
    "Given a Posix timestamp, return a Cocoa epoch timestamp"
    return unixepochtime - 978307200.0
