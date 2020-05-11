"""This module contains classes and functions to work with item discounts"""
from .base import TouchBistroDBObject, TouchBistroObjectList
from .dates import cocoa_2_datetime
from .waiter import Waiter

#: This tuple maps the ZI_TYPE column to whether or not this is a void
#: or a discount (both are stored as discounts)
DISCOUNT_TYPES = ("Void", "Discount")


class ItemDiscountList(TouchBistroObjectList):
    """Use this class to get a list of ItemDiscount objects for an OrderItem.
    It behaves like a sequence, where you can simply iterate over the object,
    or call it with an index to get a particular item.

    kwargs:
        - order_item_id
    """

    #: Query to get a list of discount PK's for this order item
    QUERY = """SELECT
        ZUUID
        FROM ZDISCOUNT
        WHERE ZORDERITEM = :order_item_id
        ORDER BY ZI_INDEX ASC
        """

    def total(self):
        "Returns the total value of all discounts in the list"
        amount = 0.0
        for discount in self.items:
            amount += discount.amount
        return amount

    @property
    def items(self):
        "Returns the discounts as a list, caching db results"
        if self._items is None:
            self._items = list()
            for row in self._fetch_items():
                self._items.append(
                    ItemDiscount(
                        self._db_location,
                        discount_uuid=row['ZUUID']))
        return self._items

    def _fetch_items(self):
        """Returns a list of discount uuids from the DB for this order
        item"""
        bindings = {
            'order_item_id': self.kwargs.get('order_item_id')}
        return self.db_handle.cursor().execute(
            self.QUERY, bindings
        ).fetchall()


class ItemDiscount(TouchBistroDBObject):
    """This class represents a single discount on an OrderItem.

    OrderItems may have more than one discount applied.

    Required kwargs:

        - db_location: path to the database file
        - discount_uuid: the UUID for this discount
    """

    META_ATTRIBUTES = ['discount_uuid', 'discount_id', 'datetime', 'amount',
                       'discount_type', 'description', 'returns_inventory',
                       'taxable',
                       'order_item_id', 'waiter_uuid', 'authorizer_uuid']

    #: Query to get details about this discount
    QUERY = """SELECT
        *
        FROM ZDISCOUNT
        WHERE ZUUID = :discount_uuid
        """

    def __init__(self, db_location, **kwargs):
        super(ItemDiscount, self).__init__(db_location, **kwargs)
        self.discount_uuid = kwargs.get('discount_uuid')

    @property
    def discount_id(self):
        "Returns the Z_PK ID for this discount (ZUUID better for fetch)"
        return self.db_details['Z_PK']

    @property
    def discount_type(self):
        "Map to the ZI_TYPE colum for the discount"
        return DISCOUNT_TYPES[self.db_details['ZI_TYPE']]

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

    def get_waiter(self):
        "Returns a Waiter object for the person who initiated the discount"
        return Waiter(self._db_location, waiter_uuid=self.waiter_uuid)

    def get_authorizer(self):
        "Returns a Waiter object for the person that authorized the discount"
        return Waiter(self._db_location, waiter_uuid=self.authorizer_uuid)

    def _fetch_entry(self):
        """Returns the db row for this discount"""
        bindings = {
            'discount_uuid': self.discount_uuid}
        return self.db_handle.cursor().execute(
            self.QUERY, bindings
        ).fetchone()

    def receipt_form(self):
        """Print the discount in a format suitable for receipts"""
        return (
            f"- ${self.amount:.2f}: {self.description} "
            f"{self.discount_type}\n")
