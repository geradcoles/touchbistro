"""This module provides the base classes required for various other
modules representing TouchBistro objects.
"""
from .tbdatabase import TouchBistroDBQueryResult


class TouchBistroDBObject(TouchBistroDBQueryResult):
    """
    This class provides a base object for database operations in
    TouchBistro.
    """

    META_ATTRIBUTES = []

    @property
    def uuid(self):
        """All objects should have UUID associated with them from ZUUID"""
        return self.db_results['ZUUID']

    @property
    def db_results(self):
        """Return the first db result since there should always be one"""
        try:
            return super(TouchBistroDBObject, self).db_results[0]
        except IndexError:
            return None

    def summary(self):
        """Returns a dictionary version of the change"""
        output = {'meta': dict()}
        for attr in self.META_ATTRIBUTES:
            output['meta'][attr] = getattr(self, attr)
        return output

    def __str__(self):
        "Return a string-formatted version of this object"
        summary = self.summary()
        output = f"{self.__class__.__name__}(\n"
        for attr in self.META_ATTRIBUTES:
            output += f"  {attr}: {summary[attr]}\n"
        output += ")"
        return output


class TouchBistroObjectList(TouchBistroDBQueryResult):
    """This class represents a list of objects and provides a sequence-type
    interface. You can iterate over this List, use index syntax obj_list[2],
    and get a length for the item list as with a normal list.
    """

    def __init__(self, db_location, **kwargs):
        """Initialize the class"""
        super(TouchBistroObjectList, self).__init__(db_location, **kwargs)
        self._items = None

    @property
    def items(self):
        "Returns a list of vivified objects"
        if self._items is None:
            self._items = list()
            for row in self.db_results:
                self._items.append(self._vivify_db_row(row))
        return self._items

    def summary(self):
        "Return a summary of the item list"
        output = list()
        for item in self.items:
            output.append(item.summary())
        return output

    def _vivify_db_row(self, row):
        """Implement in a subclass to provide mechanism to convert a db row
        into the object type returned by items() above."""
        raise NotImplementedError("_vivify_db_row has not been implemented")

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
