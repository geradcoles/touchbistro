"""This module provides the base classes required for various other
modules representing TouchBistro objects.
"""
import logging
import sqlite3


class TouchBistroDB():
    """
    This class provides a base object for database operations in
    TouchBistro.
    """

    def __init__(self, db_location, **kwargs):
        self.log = logging.getLogger(self.__class__.__module__)
        self.dry_run = kwargs.get('dry_run', False)
        self._db_location = db_location
        self.kwargs = kwargs
        self.__db_handle = None
        self.__cursor = None

    @property
    def db_handle(self):
        "Returns an sqlite3 database handle"
        if self.__db_handle is None:
            self.log.debug('getting an sqlite3 database handle')
            self.__db_handle = sqlite3.connect(self._db_location)
            self.__db_handle.row_factory = sqlite3.Row
        return self.__db_handle
