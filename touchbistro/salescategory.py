"""This class represents sales categories and provides objects and methods
to report on them.

Sales categories are found in the ZITEMTYPE table, and can by sourced
by the ZTYPEID column, referenced from the ZTYPE column on a MenuItem.
"""
import sqlite3
import logging
from .base import TouchBistroDB
from .dates import cocoa_2_datetime


class SalesCategory(TouchBistroDB):
    """This class represents a sales category from the ZITEMTYPE table

    kwargs:

        - sales_type_id: an ID for the sales category type
        - sales_type_uuid: a uuid for the sales category type

    One or both of the above may be supplied, UUID will be preferred.
    """

    #: These attributes will be part of the dictionary representation
    #: of this object, as well as the string version.
    META_ATTRIBUTES = ['category_uuid', 'category_type_id', 'name',
                       'created_date']

    #: Query to get details about this object by UUID
    QUERY_BY_UUID = """SELECT
            *
        FROM ZITEMTYPE
        WHERE ZUUID = :value
        """

    #: Query to get details about this object by integer key
    QUERY_BY_ID = """SELECT
            *
        FROM ZITEMTYPE
        WHERE ZTYPEID = :value
        """

    def __init__(self, db_location, **kwargs):
        super(SalesCategory, self).__init__(db_location, **kwargs)
        self.log = logging.getLogger("{}.{}".format(
            self.__class__.__module__, self.__class__.__name__
        ))
        self._db_details = kwargs.get('db_details', None)

    @property
    def category_uuid(self):
        "Returns the UUID for this category"
        return self.db_details['ZUUID']

    @property
    def category_type_id(self):
        "Returns the ZTYPEID key for the sales category"
        return self.db_details['ZTYPEID']

    @property
    def created_date(self):
        "Returns a tz-aware datetime object for when the category was created"
        try:
            return cocoa_2_datetime(self.db_details['ZCREATEDATE'])
        except TypeError:
            return None

    @property
    def name(self):
        "Returns the name of the sales category"
        return self.db_details['ZNAME']

    @property
    def db_details(self):
        "Returns cached results for the :attr:`QUERY` specified above"
        if self._db_details is None:
            self._db_details = dict()
            result = self._fetch_entry()
            for key in result.keys():
                # perform the dict copy
                self._db_details[key] = result[key]
            # self.log.debug(self._db_details)
        return self._db_details

    def summary(self):
        """Returns a dictionary version of the change"""
        output = dict()
        for attr in self.META_ATTRIBUTES:
            self.log.debug("attribute: %s", attr)
            output[attr] = getattr(self, attr)
        return output

    def _fetch_entry(self):
        """Returns the db row for this sales category entry"""
        sqlite3.enable_callback_tracebacks(True)
        bindings = dict()
        if self.kwargs.get('category_uuid', None) is not None:
            self.log.debug(
                "querying sales category by uuid %s",
                self.kwargs.get('category_uuid'))
            bindings['value'] = self.kwargs.get('category_uuid')
            return self.db_handle.cursor().execute(
                self.QUERY_BY_UUID, bindings).fetchone()
        if self.kwargs.get('category_type_id', None) is not None:
            self.log.debug(
                "querying sales category by type id %s",
                self.kwargs.get('category_type_id'))
            bindings['value'] = self.kwargs.get('category_type_id')
            return self.db_handle.cursor().execute(
                self.QUERY_BY_ID, bindings).fetchone()
        self.log.error(
            "trying to fetch sales category with kwargs %s", self.kwargs)
        return None

    def __str__(self):
        "Return a string-formatted version of this change"
        summary = self.summary()
        output = "SalesCategory(\n"
        for attr in self.META_ATTRIBUTES:
            output += f"  {attr}: {summary[attr]}\n"
        output += ")"
        return output
