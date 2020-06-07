import csv
from .reports import (
    explode_order, explode_loyalty, explode_order_fields,
    explode_loyalty_fields)

CSV_DATE_FORM = '%Y-%m-%d %I:%M:%S %p'


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


def write_loyalty_to_csv(handle, loyalty):
    "Output the orders as CSV data"
    writer = csv.DictWriter(
        handle, dialect='excel', fieldnames=explode_loyalty_fields())
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
