"""This module contains classes and functions to work with item discounts"""
import logging
from lib7shifts.cmd.common import Sync7Shifts2Sqlite
from .dates import cocoa_2_datetime
from .waiter import Waiter


class ItemDiscount(Sync7Shifts2Sqlite):
    """This class represents a single discount on an OrderItem.

    OrderItems may have more than one discount applied.

    Required kwargs:

        - db_location: path to the database file
        - discount_uuid: the UUID for this discount
    """

    #: Query to get details about this discount
    QUERY = """SELECT
        *
        FROM ZDISCOUNT
        WHERE ZUUID = :discount_uuid
        """

    def __init__(self, db_location, **kwargs):
        super(ItemDiscount, self).__init__(db_location, **kwargs)
        self.log = logging.getLogger("{}.{}".format(
            self.__class__.__module__, self.__class__.__name__
        ))
        self.discount_uuid = kwargs.get('discount_uuid')
        self._db_details = None

    @property
    def discount_id(self):
        "Returns the Z_PK ID for this discount (ZUUID better for fetch)"
        return self.db_details['Z_PK']

    @property
    def discount_type(self):
        "Map to the ZI_TYPE colum for the discount"
        return self.db_details['ZI_TYPE']

    @property
    def description(self):
        "Returns the human-readable description for the discount"
        return self.db_details['ZDISCOUNTDESCRIPTION']

    @property
    def returns_inventory(self):
        "Returns True if this discount returns inventory"
        if self.db_details['ZRETURNSINVENTORY']:
            return True
        return False

    @property
    def taxable(self):
        "Returns True if this discount is taxable"
        if self.db_details['ZTAXABLE']:
            return True
        return False

    @property
    def order_item_id(self):
        "Returns the ID number for the OrderItem discounted"
        return self.db_details['ZORDERITEM']

    @property
    def amount(self):
        "Returns the amount discounted for the OrderItem"
        return self.db_details['ZI_AMOUNT']

    @property
    def datetime(self):
        "Returns the Datetime associated with the discount"
        return cocoa_2_datetime(self.db_details['ZVOIDDATE'])

    @property
    def waiter_uuid(self):
        "Returns the waiter UUID associated with the discount"
        return self.db_details['ZWAITERUUID']

    @property
    def authorizer_uuid(self):
        "Returns the UUID for the Waiter who authorized the discount"
        return self.db_details['ZMANAGERUUID']

    @property
    def db_details(self):
        "Returns cached results for the :attr:`QUERY` specified above"
        if self._db_details is None:
            self._db_details = dict()
            result = self._fetch_discount()
            for key in result.keys():
                # perform the dict copy
                self._db_details[key] = result[key]
        return self._db_details

    def get_waiter(self):
        "Returns a Waiter object for the person who initiated the discount"
        return Waiter(self._db_location, waiter_uuid=self.waiter_uuid)

    def get_authorizer(self):
        "Returns a Waiter object for the person that authorized the discount"
        return Waiter(self._db_location, waiter_uuid=self.authorizer_uuid)

    def _fetch_discount(self):
        """Returns the db row for this discount"""
        bindings = {
            'discount_uuid': self.discount_uuid}
        return self.db_handle.cursor().execute(
            self.QUERY, bindings
        ).fetchone()

    def receipt_form(self):
        """Print the discount in a format suitable for receipts"""
        return f"- ${self.amount:3.2f}: {self.description}\n"

    def summary(self):
        """Returns a dictionary containing a summary of this discount"""
        summary = {'meta': dict()}
        fields = ['discount_uuid', 'discount_id', 'datetime', 'amount',
                  'discount_type', 'description', 'returns_inventory',
                  'taxable',
                  'order_item_id', 'waiter_uuid', 'authorizer_uuid']
        for field in fields:
            summary['meta'][field] = getattr(self, field)
        return summary

    def __str__(self):
        """Return a pretty string-version of the class"""
        return(
            f"ItemDiscount(\n"
            f"  uuid: {self.discount_uuid}\n"
            f"  discount_id: {self.discount_id}\n"
            f"  datetime: {self.datetime}\n"
            f"  amount: {self.amount}\n"
            f"  discount_type: {self.discount_type}\n"
            f"  description: {self.description}\n"
            f"  returns_inventory: {self.returns_inventory}\n"
            f"  taxable: {self.taxable}\n"
            f"  order_item_id: {self.order_item_id}\n"
            f"  waiter_uuid: {self.waiter_uuid}\n"
            f"  authorizer_uuid: {self.authorizer_uuid}\n"
            ")"
        )
