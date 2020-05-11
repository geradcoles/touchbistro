"""This class represents sales categories and provides objects and methods
to report on them.

Sales categories are found in the ZITEMTYPE table, and can by sourced
by the ZTYPEID column, referenced from the ZTYPE column on a MenuItem.
"""
from .base import TouchBistroDBObject
from .dates import cocoa_2_datetime


class SalesCategory(TouchBistroDBObject):
    """This class represents a sales category from the ZITEMTYPE table

    kwargs:

        - sales_type_uuid: a uuid for the sales category type

    """

    #: These attributes will be part of the dictionary representation
    #: of this object, as well as the string version.
    META_ATTRIBUTES = ['category_uuid', 'category_type_id', 'name',
                       'created_date']

    #: Query to get details about this object by UUID
    QUERY = """SELECT
            *
        FROM ZITEMTYPE
        WHERE ZUUID = :sales_type_uuid
        """

    QUERY_BINDING_ATTRIBUTES = ['sales_type_uuid']

    @property
    def category_uuid(self):
        "Returns the UUID for this category"
        return self.db_results['ZUUID']

    @property
    def category_type_id(self):
        "Returns the ZTYPEID key for the sales category"
        return self.db_results['ZTYPEID']

    @property
    def created_date(self):
        "Returns a tz-aware datetime object for when the category was created"
        try:
            return cocoa_2_datetime(self.db_results['ZCREATEDATE'])
        except TypeError:
            return None

    @property
    def name(self):
        "Returns the name of the sales category"
        return self.db_results['ZNAME']


class SalesCategoryByID(SalesCategory):
    """Use this class to get a sales category starting with its Z_PK primary
    key instead of UUID. Otherwise identical to SalesCategory

    kwargs:

        - sales_type_id: an ID for the sales category type

    """

    #: Query to get details about this object by integer key
    QUERY = """SELECT
            *
        FROM ZITEMTYPE
        WHERE ZTYPEID = :sales_type_id
        """

    QUERY_BINDING_ATTRIBUTES = ['sales_type_id']
