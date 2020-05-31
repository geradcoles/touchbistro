"""This module contains methods for performing reports against the database.
"""
from .order import Order, OrderItem
from .discount import ItemDiscount
from .modifier import ItemModifier
from .payment import Payment


REPORTED_OBJECTS = (
    Order, OrderItem, ItemDiscount, ItemModifier, Payment
)

ORDER_BASIC_FIELDS = ['order_number', 'bill_number']


def explode_order_fields():
    "Returns a list of fields reported by explode_order"
    fields = set()
    for obj in REPORTED_OBJECTS:
        for field in obj.meta_keys():
            fields.add(field)
    return fields


def explode_order(order):
    """Given an Order object, break it down into an iterable of dictionaries
    for every order line item, discount, and modifier. Each row will contain
    a subset of dict keys appropriate for that item type. A column called
    ObjectType will always include the class name for the item being included.
    The first item returned is the order metadata, then the first line item,
    followed by that line item's modifiers, followed by its discounts, then
    the next line item summary, with its mods and discounts. After all line
    items have been returned, a row will be included for each payment applied
    to the order, if any exist.

    Every row will include common data about the order to facilitate join-type
    operations between rows. The common order columns are defined in
    :attr:`ORDER_BASIC_FIELDS` above. Beware that column names are non-
    qualified, meaning if you specify 'uuid' as a basic field for orders,
    it may be confusing because every object also has 'uuid' in its list of
    META_ATTRIBUTES, which will overwrite the order's uuid for that row.
    """
    yield order.meta_summary()
    order_basics = dict()
    for field in ORDER_BASIC_FIELDS:
        order_basics[field] = getattr(order, field)
    for item in order.order_items:
        yield {**order_basics, **item.meta_summary()}
        for modifier in item.modifiers:
            yield {**order_basics, **modifier.meta_summary()}
        for discount in item.discounts:
            yield {**order_basics, **discount.meta_summary()}
    for payment in order.payments:
        yield {**order_basics, **payment.meta_summary()}


class SalesReport():
    """This class provides methods for generating a daily sales report that
    provides a detailed breakdown of every line item, modifier, and discount
    from every order in the specified time period.
    """
