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

    META_ATTRIBUTES = []

    QUERY = None

    def __init__(self, db_location, **kwargs):
        self.log = logging.getLogger("{}.{}".format(
            self.__class__.__module__, self.__class__.__name__
        ))
        self.dry_run = kwargs.get('dry_run', False)
        self._db_location = db_location
        self.kwargs = kwargs
        self._db_details = kwargs.get('db_details', None)
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

    @property
    def db_details(self):
        "Returns cached results for the :attr:`QUERY` specified above"
        if self._db_details is None:
            self._db_details = dict()
            result = self._fetch_entry()
            for key in result.keys():
                # perform the dict copy
                self._db_details[key] = result[key]
        return self._db_details

    def summary(self):
        """Returns a dictionary version of the change"""
        output = {'meta': dict()}
        for attr in self.META_ATTRIBUTES:
            output['meta'][attr] = getattr(self, attr)
        return output

    def _fetch_entry(self):
        """Returns the db row for this object"""
        return dict()

    def __str__(self):
        "Return a string-formatted version of this object"
        summary = self.summary()
        output = f"{self.__class__.__name__}(\n"
        for attr in self.META_ATTRIBUTES:
            output += f"  {attr}: {summary[attr]}\n"
        output += ")"
        return output


class ItemList(TouchBistroDB):
    """This class represents a list of items and provides a sequence-type
    interface
    """

    def __init__(self, db_location, **kwargs):
        """Initialize the class"""
        super(ItemList, self).__init__(db_location, **kwargs)
        self._items = None

    @property
    def items(self):
        "Returns items as a list, caching db results"
        raise NotImplementedError("Item not implemented in subclass")

    def summary(self):
        "Return a summary of the item list"
        output = list()
        for item in self.items:
            output.append(item.summary())
        return output

    def __len__(self):
        "Return the number of db results"
        return len(self.items)

    def __iter__(self):
        "Provide a method for iterating over rows"
        for row in self.items:
            yield row

    def __getitem__(self, key):
        "Return the item at index key"
        return self.items[key]

    def _fetch_items(self):
        """Returns a list of item ids from the DB"""
        raise NotImplementedError("_fetch_items not implemented in subclass")
