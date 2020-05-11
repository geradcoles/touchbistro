"""This module provides methods and classes for reading the TouchBistro
change log, found in the ZCHANGELOG table.

This table contains records of many kinds of changes, and I'm not sure of
the total extent of recorded changes at this time, but it looks like some
kinds of changes are excluded (such as creating a new order), however this
may turn out to be untrue.

The changelog provides references to many different kinds of objects in the
TouchBistro database, which could lead to circular dependencies amongst
modules. To limit this, most imports are performed at call time rather than at
library load. In this way, if a Waiter object is looking at the log of waiter
changes, it can directly load waiter objects from the log rather than using
convenience methods found within a ChangeLogEntry.
"""
from .base import TouchBistroDBObject
from .dates import cocoa_2_datetime, datetime_2_cocoa


class SearchChangeLog(TouchBistroDBObject):
    """This class provides a mechanism for conveniently searching the changelog
    based on arbitrary criteria. Search results are simply yielded out as
    iterables of ChangeLogEntry objects.

    At the time of this writing, TouchBistro has a bug where the reference id
    for changes to TakeoutOrders is not populated in the table, so they are
    impossible to tie back to the object being changed.

    For many orders, it is helpful to look for changes both by order number
    and by bill number.
    """

    #: This is the query used to fetch change to orders by order number.
    #: Results will be returned from oldest to newest.
    QUERY_BY_REFERENCE = """SELECT
            *
        FROM ZCHANGELOG
        WHERE
            ZOBJECTREFERENCETYPE = :reftype AND
            ZOBJECTREFERENCE = :ref
        ORDER BY Z_PK ASC
        """

    #: Fetch all changes of the given type for the given time period.
    #: Results will be returned from newest to oldest.
    QUERY_BY_CHANGETYPE = """SELECT
            *
        FROM ZCHANGELOG
        WHERE
            ZCHANGETYPE = :change_type AND
            ZTIMESTAMP >= :earliest_time AND
            ZTIMESTAMP < :cutoff_time
        ORDER BY Z_PK DESC
    """

    def get_changes_by_order_number(self, order_number):
        """Returns all changes for the order corresponding to the
        order_number provided"""
        return self._fetch_by_reference('OrderNumber', order_number)

    def get_changes_by_bill_number(self, bill_number):
        """Returns a list of changes by change type"""
        return self._fetch_by_reference('BillNumber', bill_number)

    def get_all_menu_changes(self, earliest_time, cutoff_time):
        """Returns all menu changes for the given timeframe (newest first).

        earliest_time and cutoff_time should be tz-aware datetime objects"""
        return self._fetch_by_change_type(
            'MenuItemChange', earliest_time, cutoff_time)

    def _fetch_by_reference(self, reference_type, reference):
        """Pass in a reference type and a reference id and this will
        run the DB query to fetch matching ChangeLogEntry objects.
        """
        bindings = {'reftype': reference_type, 'ref': reference}
        for row in self.db_handle.cursor().execute(
                self.QUERY_BY_REFERENCE, bindings).fetchall():
            yield ChangeLogEntry.from_db_row(self._db_location, row)

    def _fetch_by_change_type(self, change_type, earliest_time, cutoff_time):
        """Given a change type, earliest_time and cutoff_time (in datetime
        format), return a list of matching changes in order of newest
        to oldest"""
        bindings = {'change_type': change_type,
                    'earliest_time': datetime_2_cocoa(earliest_time),
                    'cutoff_time': datetime_2_cocoa(cutoff_time)}
        for row in self.db_handle.cursor().execute(
                self.QUERY_BY_CHANGETYPE, bindings).fetchall():
            yield ChangeLogEntry.from_db_row(self._db_location, row)


class ChangeLogEntry(TouchBistroDBObject):
    """This class represents a change log entry in the ZCHANGELOG table

    kwargs:

        - changelog_uuid: a uuid for the changelog entry
    """

    #: These attributes will be part of the dictionary representation
    #: of this object, as well as the string version.
    META_ATTRIBUTES = ['changelog_uuid', 'change_id', 'timestamp',
                       'change_type', 'change_type_details',
                       'object_reference',
                       'object_reference_type', 'user_uuid',
                       'value_changed_from', 'value_changed_to']

    #: Query to get details about this discount
    QUERY = """SELECT
        *
        FROM ZCHANGELOG
        WHERE ZUUID = :changelog_uuid
        """

    def __init__(self, db_location, **kwargs):
        super(ChangeLogEntry, self).__init__(db_location, **kwargs)
        self.changelog_uuid = kwargs.get('changelog_uuid')

    @property
    def change_id(self):
        """Returns a Z_PK integer change id for the change, but changelog_uuid
        is best"""
        return self.db_details['Z_PK']

    @property
    def timestamp(self):
        "Returns a datetime corresponding to the time of the change"
        return cocoa_2_datetime(self.db_details['ZTIMESTAMP'])

    @property
    def change_type(self):
        """Returns the type of change"""
        return self.db_details['ZCHANGETYPE']

    @property
    def change_type_details(self):
        """Returns details about the type of change"""
        return self.db_details['ZCHANGETYPEDETAILS']

    @property
    def object_reference(self):
        """Returns a reference to the object being changed (uuid or PK etc)"""
        return self.db_details['ZOBJECTREFERENCE']

    @property
    def object_reference_type(self):
        """Returns the type of object being changed"""
        return self.db_details['ZOBJECTREFERENCETYPE']

    @property
    def user_uuid(self):
        """Returns the uuid of the user that initiated the change"""
        return self.db_details['ZUSER']

    @property
    def value_changed_from(self):
        """Returns the value of the object reference before the change, if
        applicable"""
        return self.db_details['ZVALUECHANGEDFROM']

    @property
    def value_changed_to(self):
        """Returns the value of the object reference after the change, if
        applicable"""
        return self.db_details['ZVALUECHANGEDTO']

    @classmethod
    def from_db_row(cls, db_location, rowdata):
        """Populate and return a ChangeLogEntry object directly from a db
        result row"""
        db_details = dict()
        for key in rowdata.keys():
            db_details[key] = rowdata[key]
        obj = cls(db_location,
                  changelog_uuid=rowdata['ZUUID'], db_details=db_details)
        return obj

    def _fetch_entry(self):
        """Returns the db row for this changelog entry"""
        bindings = {
            'changelog_uuid': self.changelog_uuid}
        return self.db_handle.cursor().execute(
            self.QUERY, bindings
        ).fetchone()
