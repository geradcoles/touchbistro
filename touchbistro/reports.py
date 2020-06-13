"""This module contains methods for performing reports against the database.
"""
import sys
import csv
import json
from .order import Order, OrderFromId, OrderItem
from .discount import ItemDiscount
from .modifier import ItemModifier
from .payment import Payment
from .loyalty import LoyaltyActivity, get_loyalty_for_date_range


CSV_DATE_FORM = '%Y-%m-%d %I:%M:%S %p'


REPORTED_OBJECTS = (
    Order, OrderItem, ItemDiscount, ItemModifier, Payment
)

#: These fields from a top-level Order object will always be output
ORDER_BASIC_FIELDS = ['bill_number', 'order_number', 'order_type',
                      'custom_takeout_type']

#: Define the attributes to include in order reports
ORDER_REPORT_FIELDS = {
    Order: (
        'table_name',
        'party_name',
        'party_size',
        'custom_takeout_type',
        'waiter_name',
        'datetime',
        'subtotal',
        'taxes',
        'total',
        'object_type',
    ),
    OrderFromId: (
        'table_name',
        'party_name',
        'party_size',
        'custom_takeout_type',
        'waiter_name',
        'datetime',
        'subtotal',
        'taxes',
        'total',
        'object_type',
    ),
    OrderItem: (
        'datetime',
        'quantity',
        'name',
        'sales_category',
        'price',
        'waiter_name',
        'was_sent',
        'object_type',
    ),
    ItemDiscount: (
        'datetime',
        'waiter_name',
        'name',
        'authorizer_name',
        'discount_type',
        'object_type',
    ),
    ItemModifier: (
        'name',
        'datetime',
        'price',
        'sales_category',
        'waiter_name',
        'object_type',
    ),
    Payment: (
        'datetime',
        'payment_number',
        'payment_type',
        'tip',
        'amount',
        'change',
        'balance',
        'customer_account_name',
        'customer_id',
        'card_type',
        'auth_number',
        'object_type',
    ),
    LoyaltyActivity: (
        'datetime',
        'balance_change',
        'account_number',
        'waiter_name',
        'transaction_id',
        'object_type',
    )
}


def explode_order_fields():
    "Returns a list of fields reported by explode_order"
    return (
        'bill_number', 'order_number', 'datetime', 'order_type',
        'object_type', 'bill_waiter', 'party_size',
        'custom_takeout_type', 'discount_type',
        'waiter_name', 'name', 'sales_category', 'quantity', 'price',
        'subtotal', 'taxes', 'total', 'tip', 'amount', 'change', 'balance',
        'payment_type', 'payment_number', 'party_name',
        'customer_account_name', 'balance_change', 'account_number',
        'was_sent', 'authorizer_name', 'card_type',
        'auth_number', 'table_name',
        'customer_id', 'transaction_id')


def explode_loyalty_fields():
    "Returns a list of fields reported by explode_loyalty"
    return ORDER_REPORT_FIELDS[LoyaltyActivity]


def explode_loyalty(loyalty):
    """Given a set of loyalty items (as a list-type object), explode them into
    fields suitable for reporting"""
    output = {}
    for field in ORDER_REPORT_FIELDS[LoyaltyActivity]:
        output[field] = getattr(loyalty, field)
    return output


def get_obj_fields(obj):
    """Given a supported reporting object type, get relevant fields and return
    as a dictionary of field-value pairs"""
    output = dict()
    for key in ORDER_REPORT_FIELDS[obj.__class__]:
        output[key] = getattr(obj, key)
    return output


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
    order_basics = dict()
    for field in ORDER_BASIC_FIELDS:
        order_basics[field] = getattr(order, field)
    # add this here because we don't want to lose the waiter_name from line
    order_basics['bill_waiter'] = order.waiter_name
    yield {**order_basics, **get_obj_fields(order)}
    for item in order.order_items:
        if item.was_voided():
            # voided items have sales associated with categories, and discounts
            # as well, which will cause reporting errors if allowed through.
            continue
        yield {**order_basics, **get_obj_fields(item)}
        yield from explode_modifiers(order_basics, item.modifiers)
        yield from explode_discounts(order_basics, item)
    for payment in order.payments:
        yield {**order_basics, **get_obj_fields(payment)}
        if payment.is_loyalty():
            yield {**order_basics, **get_obj_fields(payment.loyalty_activity)}


def explode_discounts(order_basics, item):
    """Yields a report line item for ItemDiscounts, broken down by each sales
    category associated with the discount"""
    gross = item.gross_sales_by_sales_category()
    for discount in item.discounts:
        sales_categories = discount.price_by_sales_category(gross)
        for category, amount in sales_categories.items():
            yield {
                **order_basics, **get_obj_fields(discount),
                'sales_category': category,
                'price': amount
            }


def explode_modifiers(order_basics, modifiers, depth=0):
    """Explode modifiers, with nesting support"""
    for modifier in modifiers:
        yield {**order_basics, **get_obj_fields(modifier)}
        yield from explode_modifiers(
            order_basics, modifier.nested_modifiers, depth=depth+1)


def loyalty_report(db_path, earliest_date, latest_date, day_boundary, output,
                   in_csv=False, in_json=False, order_rept=False):
    "Dump loyalty in the specified output format"
    suffix = ''
    if order_rept:
        suffix = 'ReportItem'
    loyalty = get_loyalty_for_date_range(
        db_path, earliest_date=earliest_date,
        latest_date=latest_date, day_boundary=day_boundary,
        object_type_suffix=suffix)
    header = True
    if in_csv:
        fields = explode_loyalty_fields()
        if order_rept:
            fields = explode_order_fields()
            header = False
        write_loyalty_to_csv(output, loyalty, header=header, fields=fields)
    elif in_json:
        for item in loyalty:
            if output == sys.stdout:
                print(json.dumps(
                    item.summary(), indent=4, sort_keys=True, default=str))
            else:
                json.dump(item.summary(), output, sort_keys=True, default=str)
    else:
        for loyalty_item in loyalty:
            print(loyalty_item.summary())


def format_datetime(order_item):
    """Converts datetimes to strings for CSV output"""
    if order_item.get('datetime', None):
        order_item['datetime'] = order_item['datetime'].strftime(CSV_DATE_FORM)
    if order_item.get('sent_time', None):
        order_item['sent_time'] = order_item['sent_time'].strftime(
            CSV_DATE_FORM)
    return order_item


def write_orders_to_csv(handle, orders):
    "Output the orders as CSV data"
    writer = csv.DictWriter(
        handle, dialect='excel', fieldnames=explode_order_fields())
    writer.writeheader()
    for order in orders:
        for lineitem in explode_order(order):
            order_item = format_datetime(lineitem)
            writer.writerow(order_item)


def write_loyalty_to_csv(
        handle, loyalty, header=True, fields=explode_loyalty_fields()):
    "Output the orders as CSV data"
    writer = csv.DictWriter(
        handle, dialect='excel', fieldnames=fields)
    if header:
        writer.writeheader()
    for item in loyalty:
        item = format_datetime(explode_loyalty(item))
        writer.writerow(item)


def write_order_to_csv(handle, order):
    "Output the exploded order as CSV data"
    writer = csv.DictWriter(
        handle, dialect='excel', fieldnames=explode_order_fields())
    writer.writeheader()
    for lineitem in explode_order(order):
        order_item = format_datetime(lineitem)
        writer.writerow(order_item)
