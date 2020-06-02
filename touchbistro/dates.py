"""Common functions and definitions for date handling"""
from datetime import datetime, timezone

DEFAULT_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DEFAULT_DATE_FORMAT = '%Y-%m-%d'

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


def get_local_tz():
    "Return the current local timezone"
    return datetime.utcnow().astimezone().tzinfo


def to_datetime(date_string, tzinfo=timezone.utc):
    """Given a datetime string in API format, return a
    :class:`datetime.datetime` object corresponding to the date and time"""
    date = datetime.strptime(
        date_string, DEFAULT_DATETIME_FORMAT)
    return date.replace(tzinfo=tzinfo)


def to_date(date_string, tzinfo=timezone.utc):
    """Given a date string in YYYY-MM-DD format, return a
    :class:`datetime.datetime` object corresponding to the date at 12AM"""
    date = datetime.strptime(
        date_string, DEFAULT_DATE_FORMAT)
    return date.replace(tzinfo=tzinfo)


def to_local_date(date_string):
    """Returns a :class:`DateTime7Shifts` object for the specified date
    string (YYYY-MM-DD form), in the local timezone."""
    return to_date(date_string, tzinfo=get_local_tz())


def to_local_datetime(date_string):
    """Returns a :class:`DateTime7Shifts` object for the specified date
    and time string (YYYY-MM-DD HH:MM:SS form), in the local timezone."""
    return to_datetime(date_string, tzinfo=get_local_tz())


def _get_epoch_ts_for_date(date):
    "Given a local date of form YYYY-MM-DD, return a unix TS"
    return to_date(date, tzinfo=get_local_tz()).timestamp()


def from_datetime(dt_obj):
    """Converts the datetime object back into a text representation compatible
    with the 7shifts API"""
    return dt_obj.__str__()


def to_y_m_d(dt_obj):
    """Converts a datetime object to text in YYYY-MM-DD format"""
    return dt_obj.strftime("%Y-%m-%d")


def to_h_m_s(dt_obj):
    """Outputs just the time-portion of a datetime object in HH:MM:SS form"""
    return dt_obj.strftime("%H:%M:%S")
