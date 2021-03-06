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

    QUERY_BINDING_ATTRIBUTES = ['order_item_id']

    def total(self):
        "Returns the total value of all discounts in the list"
        amount = 0.0
        for discount in self.items:
            amount += discount.price
        return amount

    def _vivify_db_row(self, row):
        return ItemDiscount(
            self._db_location,
            discount_uuid=row['ZUUID'],
            parent=self.parent)


class ItemDiscount(TouchBistroDBObject):
    """This class represents a single discount on an OrderItem.

    OrderItems may have more than one discount applied.

    Required kwargs:

        - db_location: path to the database file
        - discount_uuid: the UUID for this discount
    """

    META_ATTRIBUTES = ['datetime', 'amount', 'waiter_name', 'authorizer_name',
                       'discount_type', 'name', 'returns_inventory',
                       'taxable',
                       'order_item_id', 'waiter_uuid', 'authorizer_uuid']

    #: Query to get details about this discount
    QUERY = """SELECT
        *
        FROM ZDISCOUNT
        WHERE ZUUID = :discount_uuid
        """

    QUERY_BINDING_ATTRIBUTES = ['discount_uuid']

    def __init__(self, db_location, **kwargs):
        super(ItemDiscount, self).__init__(db_location, **kwargs)
        self._waiter = None
        self._authorizer = None

    @property
    def discount_type(self):
        "Map to the ZI_TYPE colum for the discount"
        return DISCOUNT_TYPES[self.db_results['ZI_TYPE']]

    @property
    def name(self):
        "Returns the human-readable description for the discount"
        return self.db_results['ZDISCOUNTDESCRIPTION']

    @property
    def returns_inventory(self):
        "Returns True if this discount returns inventory"
        if self.db_results['ZRETURNSINVENTORY']:
            return True
        return False

    @property
    def taxable(self):
        "Returns True if this discount is taxable"
        if self.db_results['ZTAXABLE']:
            return True
        return False

    @property
    def order_item_id(self):
        "Returns the ID number for the OrderItem discounted"
        return self.db_results['ZORDERITEM']

    @property
    def amount(self):
        "Returns the amount discounted for the OrderItem"
        if self.is_void():
            # discount behaviour is very strange around voids. The discount
            # ZI_AMOUNT column sometimes has the total line item amount, other
            # times it does not. No matter what way it is stored here, the void
            # should equal the amount of the parent line item, so we will just
            # output that to avoid subtle bugs.
            return self.parent.gross
        return self.parent.quantity * self.db_results['ZI_AMOUNT']

    @property
    def price(self):
        "Same as amount, but with correct sign"
        return - self.amount

    @property
    def datetime(self):
        "Returns the Datetime associated with the discount"
        return cocoa_2_datetime(self.db_results['ZVOIDDATE'])

    @property
    def waiter_uuid(self):
        "Returns the waiter UUID associated with the discount"
        return self.db_results['ZWAITERUUID']

    @property
    def authorizer_uuid(self):
        "Returns the UUID for the Waiter who authorized the discount"
        return self.db_results['ZMANAGERUUID']

    @property
    def waiter(self):
        "Returns a Waiter object for the person who initiated the discount"
        if self._waiter is None:
            self._waiter = Waiter(
                self._db_location,
                waiter_uuid=self.waiter_uuid,
                parent=self)
        return self._waiter

    @property
    def authorizer(self):
        "Returns a Waiter object for the person that authorized the discount"
        if self._authorizer is None:
            self._authorizer = Waiter(
                self._db_location,
                waiter_uuid=self.authorizer_uuid,
                parent=self)
        return self._authorizer

    @property
    def waiter_name(self):
        "Returns the name of the waiter that requested the discount"
        return self.waiter.display_name

    @property
    def authorizer_name(self):
        "Returns the name of the waiter that authorized the discount"
        try:
            return self.authorizer.display_name
        except TypeError:
            return None

    def price_by_sales_category(self, gross_sales_breakdown, output=None):
        """Reports back on the sales categories impacted by this discount. This
        is complicated because a discount may apply to an order item with
        nested modifiers, any of which may be associated with a different sales
        category that the top-level order item. So this code has to look at the
        parent OrderItem and collect it's Sales Category breakdown, then
        pro-rate the discount value across those Sales Categories based on
        their portion of the total for the line item including all modifiers.

        Returns a dictionary where the keys are SalesCategory objects, and the
        values are the amounts applied to each category. Supports recursion or
        cumulative math if you pass in the output dictionary."""
        if output is None:
            output = dict()
        gross = 0.0
        for category in gross_sales_breakdown.keys():
            gross += gross_sales_breakdown[category]
        for cat, amount in gross_sales_breakdown.items():
            if cat in output:
                output[cat] += self.price * amount / gross
            else:
                output[cat] = self.price * amount / gross
        return output

    def is_void(self):
        "Returns true if this is a void rather than a discount"
        if self.discount_type.upper() == "VOID":
            return True
        return False

    def receipt_form(self):
        """Print the discount in a format suitable for receipts"""
        return (
            f"- ${self.amount:.2f}: {self.name} "
            f"{self.discount_type}\n")
