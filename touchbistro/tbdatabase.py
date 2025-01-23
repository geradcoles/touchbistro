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

    #: This program runs single threaded and only needs one handle, centralize
    #: it here.
    __db_handle = None

    #: Set this to False if you really want to open the database in write mode
    #: (must be set as a class variable)
    _DB_READ_ONLY = True

    def __init__(self, db_location, **kwargs):
        self.log = logging.getLogger("{}.{}".format(
            self.__class__.__module__, self.__class__.__name__
        ))
        self.dry_run = kwargs.get('dry_run', False)
        self._db_location = db_location
        self._db_results = kwargs.get('db_results', None)
        self.kwargs = kwargs
        self._bindings = None
        self.__cursor = None

    @property
    def db_uri(self):
        """Returns the URI used to connect to the database"""
        uri = f'file:{self._db_location}'
        if TouchBistroDBQueryResult._DB_READ_ONLY:
            uri += '?mode=ro'
        return uri

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
                    self.QUERY, self.bindings, result_dict)
                self._db_results.append(result_dict)
        return self._db_results

    @property
    def db_handle(self):
        "Returns an sqlite3 database handle"
        if TouchBistroDBQueryResult.__db_handle is None:
            self.log.debug(
                'getting an sqlite3 database handle at %s',
                self.db_uri)
            handle = sqlite3.connect(self.db_uri, uri=True)
            handle.row_factory = sqlite3.Row
            handle.cursor().execute(
                f"PRAGMA cache_size = -{SQLITE3_CACHE_SIZE:d}")
            TouchBistroDBQueryResult.__db_handle = handle
        return TouchBistroDBQueryResult.__db_handle

    @property
    def bindings(self):
        """Assemble a dictionary of query bindings based on
        :attr:`QUERY_BINDING_ATTRIBUTES`."""
        if self._bindings is None:
            self._bindings = dict()
            for attr in self.QUERY_BINDING_ATTRIBUTES:
                self._bindings[attr] = self.kwargs.get(attr)
        return self._bindings

    @property
    def object_type(self):
        "Returns the name of this object's class plus any specified suffix"
        return self.__class__.__name__ + self.object_type_suffix

    @property
    def object_type_suffix(self):
        """If the 'object_type_suffix' kwarg  was passed in, return it,
        otherwise an empty string. Useful in reports where the obj_type field
        is included and you want a custom suffix to differentiate one set of
        objects from another, even when they share the same class"""
        return self.kwargs.get('object_type_suffix', '')

    def close_db(self):
        """Provides a method to force the db connection closed in situations where leaving it open might cause problems."""
        if TouchBistroDBQueryResult.__db_handle is None:
            return True
        TouchBistroDBQueryResult.__db_handle.close()
        TouchBistroDBQueryResult.__db_handle = None

    def _fetch_from_db(self):
        """Returns the db result rows for the QUERY"""
        return self.db_handle.cursor().execute(
            self.QUERY, self.bindings
        ).fetchall()
