"""This module provides base objects and attributes for working with the
TouchBistro Sqlite3 database"""
import logging
import sqlite3

#: Specify the Sqlite3 cache size in KiB
SQLITE3_CACHE_SIZE = 10 * 1024


class TouchBistroDBQueryResult():
    """This class provides a very basic wrapper around the Sqlite3 connection
    and cursor objects"""

    #: The database query to run. Specify filter attributes as :attrname,
    #: where the attribute name is the same as it is stored in self.
    QUERY = None

    #: Provide a list of kwargs to use as query bindings
    #: (the arg name should be used in the QUERY above)
    QUERY_BINDING_ATTRIBUTES = []

    def __init__(self, db_location, **kwargs):
        self.log = logging.getLogger("{}.{}".format(
            self.__class__.__module__, self.__class__.__name__
        ))
        self.dry_run = kwargs.get('dry_run', False)
        self._db_location = db_location
        self._db_results = kwargs.get('db_results', None)
        self.kwargs = kwargs
        self._bindings = None
        self.__db_handle = None
        self.__cursor = None

    @property
    def db_results(self):
        "Returns cached results for the :attr:`QUERY` specified above"
        if self._db_results is None:
            self._db_results = list()
            for result in self._fetch_from_db():
                result_dict = dict()
                for key in result.keys():
                    # perform the dict copy
                    result_dict[key] = result[key]
                self.log.debug(
                    "QUERY: \n%s\nBINDING: %s\nRESULT: %s",
                    self.QUERY, self.QUERY_BINDING_ATTRIBUTES, result_dict)
                self._db_results.append(result_dict)
        return self._db_results

    @property
    def db_handle(self):
        "Returns an sqlite3 database handle"
        if self.__db_handle is None:
            self.log.debug('getting an sqlite3 database handle')
            self.__db_handle = sqlite3.connect(self._db_location)
            self.__db_handle.row_factory = sqlite3.Row
            self.__db_handle.cursor().execute(
                f"PRAGMA cache_size = -{SQLITE3_CACHE_SIZE:d}")
        return self.__db_handle

    @property
    def bindings(self):
        """Assemble a dictionary of query bindings based on
        :attr:`QUERY_BINDING_ATTRIBUTES`."""
        if self._bindings is None:
            self._bindings = dict()
            for attr in self.QUERY_BINDING_ATTRIBUTES:
                self._bindings[attr] = self.kwargs.get(attr)
        return self._bindings

    def _fetch_from_db(self):
        """Returns the db result rows for the QUERY"""
        return self.db_handle.cursor().execute(
            self.QUERY, self.bindings
        ).fetchall()
