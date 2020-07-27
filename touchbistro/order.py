"""Module to get information about orders, such as order totals, menu items,
etc.
"""
import decimal
from datetime import timedelta
import sqlite3
from .base import TouchBistroDBObject, TouchBistroObjectList
from .dates import cocoa_2_datetime, datetime_2_cocoa, to_local_datetime
from .discount import ItemDiscountList
from .modifier import ItemModifierList, modifier_sales_category_amounts
from .payment import PaymentGroup
from .menu import MenuItem
from .waiter import Waiter


def center(text, width, symbol=' '):
    """Center-pad a string within the given width using the given symbol"""
    pad = width - len(text)
    lpad = round(pad/2)
    rpad = pad - lpad
    return symbol * lpad + text + symbol * rpad


def takeout_type_pretty(value):
    "Returns a friendly takeout type from a mapped value"
    return ZI_TAKEOUTTYPE_MAP[value]


ZI_TAKEOUTTYPE_MAP = {
    None: 'dinein',
    0: 'takeout',
    1: 'delivery',
    2: 'bartab',
    3: 'unknown',
    4: 'onlineorder'
}


def get_orders_for_date_range(
        db_location, earliest_date, latest_date, day_boundary='02:00:00'):
    """Given an earliest and a latest date, return an OrderTimeRange object
    containing all the orders for that date period. latest_date is inclusive,
    so if you specify 2020-05-31 as the latest_date, all orders from that day
    will be included in the results.

    Dates should be in the YYYY-MM-DD format. The local timezone will be used
    by default. Use the day_boundary parameter to set a reasonable time to
    transition from one day to the next, if your restaurant has cash
    transactions after midnight (default is 02:00:00).
    """
    return OrderTimeRange(
        db_location,
        earliest_time=to_local_datetime(earliest_date + ' ' + day_boundary),
        cutoff_time=to_local_datetime(
            latest_date + ' ' + day_boundary) + timedelta(days=1)
    )


def scrub_zero_amounts(input_dict):
    """Given a dictionary like we use for the sales category breakdowns, with
    values corresponding to dollar amounts, scrub any keys out of the dict with
    zero-dollar amounts"""
    output = dict()
    for key, value in input_dict.items():
        if value != 0.0:
            output[key] = value
    return output


class OrderTimeRange(TouchBistroObjectList):
    """Use this class to get a list of orders for a given date/time range

    kwargs:
        - earliest_time (datetime object)
        - cutoff_time (datetime object)
    """

    #: Query to get a list of modifier uuids for this order item
    QUERY = """SELECT
            ZORDER
        FROM ZPAIDORDER
        WHERE
            ZPAYDATE >= :earliest_time AND
            ZPAYDATE < :cutoff_time
        ORDER BY Z_PK ASC
        """

    @property
    def bindings(self):
        """Assemble query binding attributes by converting datetime to cocoa"""
        return {
            'earliest_time': datetime_2_cocoa(
                self.kwargs.get('earliest_time')),
            'cutoff_time': datetime_2_cocoa(
                self.kwargs.get('cutoff_time')
            )
        }

    def _vivify_db_row(self, row):
        return OrderFromId(
            self._db_location,
            order_id=row['ZORDER'],
            parent=self.parent)


class Order(TouchBistroObjectList):
    """Get information about a TouchBistro order based on its public-facing
    order number. Order is a parent to one or more PaidOrders.

    kwargs:

    - order_number
    """
    QUERY = """SELECT * FROM ZORDER
        WHERE ZORDERNUMBER = :order_number
        AND ZPAIDORDER>0 /* not sure what to do with deleted/unpaid splits */
        ORDER BY ZI_INDEX ASC"""
    QUERY_BINDING_ATTRIBUTES = ['order_number']

    @property
    def order_number(self):
        "Returns the order number corresponding to this object, if supplied"
        return self.kwargs.get('order_number')

    def _vivify_db_row(self, row):
        return PaidOrderSplit(
            self._db_location,
            paid_order_id=row['ZPAIDORDER'],
            order_number=row['ZORDERNUMBER'],
            split_id=row['ZI_INDEX'],
            table_split_by=row['ZI_SPLITBY'],
            parent=self)


class OrderFromId(Order):
    """Get a list of splits for an order based on its ID number
    (not the order number - be careful - this is the Z_PK column). Exaclty
    the same as Order in terms of methods and attributes.

    kwargs:

    - order_id
    """
    QUERY = """SELECT * FROM ZORDER
        WHERE Z_PK = :order_id
        AND ZPAIDORDER>0 /* not sure what to do with deleted/unpaid splits */
        ORDER BY ZI_INDEX ASC
    """

    QUERY_BINDING_ATTRIBUTES = ['order_id']

    @property
    def order_number(self):
        "Raise an exception because this is not guaranteed to be here"
        raise NotImplementedError(
            "Don't try to get order_number from an OrderFromId object")


class PaidOrderSplit(TouchBistroDBObject):
    """This class represents a paid touchbistro order, which can be a single
    split on a larger order/bill. Pass in the following required kwargs:

    - paid_order_id: the id number corresponding to Z_PK in ZPAIDORDER
    - order_number: the public facing number for the order (from Order)
    - table_split_by: from the parent row in ZORDER (ZI_SPLITBY)
    - split_id
    """
    #: Query to get as much information about an order as possible, including
    #: joining across the ZCLOSEDTAKEOUT and ZCUSTOMTAKEOUTTYPE tables to
    #: enrich the results.
    QUERY = """SELECT
            ZPAIDORDER.*,
            ZCUSTOMTAKEOUTTYPE.ZNAME as CUSTOMTAKEOUTTYPE
        FROM ZPAIDORDER
        LEFT JOIN ZCLOSEDTAKEOUT ON
            ZCLOSEDTAKEOUT.Z_PK = ZPAIDORDER.ZCLOSEDTAKEOUT
        LEFT JOIN ZCUSTOMTAKEOUTTYPE ON
            ZCUSTOMTAKEOUTTYPE.Z_PK = ZCLOSEDTAKEOUT.ZCUSTOMTAKEOUTTYPE
        WHERE ZPAIDORDER.Z_PK = :paid_order_id
    """

    QUERY_BINDING_ATTRIBUTES = ['paid_order_id']

    META_ATTRIBUTES = [
        'outstanding_balance', 'split_number',
        'order_number', 'order_type', 'table_name',
        'bill_number', 'party_name', 'split_by',
        'custom_takeout_type', 'waiter_name', 'paid_datetime',
        'subtotal', 'taxes', 'total', 'party_size', 'seated_datetime'
    ]

    def __init__(self, db_location, **kwargs):
        super(PaidOrderSplit, self).__init__(db_location, **kwargs)
        self._paid_order_id = kwargs.get('paid_order_id')
        self._order_number = kwargs.get('order_number')
        self._split_id = kwargs.get('split_id')
        self._table_split_by = kwargs.get('table_split_by')
        self._order_items = None
        self._payments = None
        self._taxes = None

    @property
    def order_number(self):
        """Returns the order number from the parent Order object"""
        return self._order_number

    @property
    def order_id(self):
        """The Z_PK Order ID from the parent Order object"""
        return self.db_results['ZORDER']

    @property
    def bill_number(self):
        "Return the bill number for this paid order"
        try:
            return self.db_results['ZI_BILLNUMBER']
        except KeyError:
            return None

    @property
    def party_name(self):
        "Return the party name for this paid order"
        try:
            return self.db_results['ZPARTYNAME']
        except KeyError:
            return None

    @property
    def party_size(self):
        "Return the size of the party"
        return self.db_results['ZI_PARTYSIZE']

    @property
    def table_name(self):
        "Returns the table name for the order"
        try:
            return self.db_results['ZTABLENAME']
        except KeyError:
            return None

    @property
    def split_by(self):
        """Returns the number of ways this order was split for payment"""
        # return self._split_by
        if self.db_results['ZI_SPLIT']:
            return self.db_results['ZI_SPLIT']
        # orders that have no splits return 0 for ZI_SPLIT instead of 1
        return 1

    @property
    def table_split_by(self):
        """For order line items that are brought in from a table split, return
        the number of ways to split the item (from ZORDER, ZI_SPLITBY)"""
        return self._table_split_by

    @property
    def split_number(self):
        """Returns the split id passed into this object + 1"""
        return self._split_id + 1

    @property
    def datetime(self):
        """Returns a Python Datetime object with local timezone corresponding
        to the time that the order was seated, if available, paid otherwise"""
        # can't use seated datetime because registers are often opened and
        # reused, so order subtotals show up on wrong dates.
        return self.paid_datetime

    @property
    def seated_datetime(self):
        """Returns a Python Datetime object with local timezone corresponding
        to the time that the order was seated, if available, paid otherwise"""
        try:
            return cocoa_2_datetime(self.db_results['ZSEATEDDATE'])
        except TypeError:
            return None

    @property
    def paid_datetime(self):
        """Returns a Python Datetime object with local timezone corresponding
        to the time that the order was seated, if available, paid otherwise"""
        try:
            return cocoa_2_datetime(self.db_results['ZPAYDATE'])
        except TypeError:
            return None

    @property
    def order_type_id(self):
        "Returns the value of ZI_TAKEOUTTYPE as an integer (or None)"
        return self.db_results['ZI_TAKEOUTTYPE']

    @property
    def order_type(self):
        "Returns the order type, aka 'takeout', 'dine-in', 'delivery', etc"
        return takeout_type_pretty(self.order_type_id)

    @property
    def custom_takeout_type(self):
        "Returns the custom takeout type associated with a takeout order"
        try:
            return self.db_results['CUSTOMTAKEOUTTYPE']
        except KeyError:
            return None

    @property
    def payment_group_id(self):
        "Returns the ID for the payment group associated with this order"
        return self.db_results['ZPAYMENTS']

    @property
    def table_order_id(self):
        """Depending on how splits are closed, the ZTABLEORDER column may be
        populated with another ZORDER order id that contains additional order
        line items, this is the ID for that order."""
        return self.db_results['ZTABLEORDER']

    @property
    def outstanding_balance(self):
        """Returns the outstanding balance amount for the order"""
        return self.db_results['ZOUTSTANDINGBALANCE']

    @property
    def loyalty_account_name(self):
        """Returns the name associated with a Loyalty account used to pay the
        order (if that was the case)"""
        return self.db_results['ZLOYALTYACCOUNTNAME']

    @property
    def loyalty_credit_balance(self):
        """Returns the credit balance of the Loyalty account used to pay the
        order (if that was the case)"""
        return self.db_results['ZLOYALTYCREDITBALANCE']

    @property
    def loyalty_point_balance(self):
        """Returns the point balance of the Loyalty account used to pay the
        order (if that was the case)"""
        return self.db_results['ZLOYALTYPOINTSBALANCE']

    @property
    def waiter_uuid(self):
        """Returns the UUID corresponding to the waiter for this PaidOrder"""
        return self.db_results['ZWAITERUUID']

    @property
    def waiter(self):
        """Return a waiter object corresponding to the paid order"""
        return Waiter(
            self._db_location,
            waiter_uuid=self.waiter_uuid,
            parent=self
        )

    @property
    def waiter_name(self):
        "Returns the display name of the waiter that closed the bill"
        try:
            return self.waiter.display_name
        except KeyError:
            return None

    @property
    def stack_tax_2_on_tax_1(self):
        """Return True if tax 2 should be stacked on tax 1 (tax on tax)"""
        if self.db_results['ZI_TAX2ONTAX1']:
            return True
        return False

    @property
    def tax_rate_1(self):
        """Returns tax rate 1 (ZI_TAX1) column, as a decimal float"""
        return self.db_results['ZI_TAX1']

    @property
    def tax_rate_2(self):
        """Returns tax rate 2 (ZI_TAX2) column, as a decimal float"""
        return self.db_results['ZI_TAX2']

    @property
    def tax_rate_3(self):
        """Returns tax rate 3 (ZI_TAX3) column, as a decimal float"""
        return self.db_results['ZI_TAX3']

    @property
    def order_items(self):
        "Lazy-load order items on the first attempt to read them, then cache"
        if self._order_items is None:
            self._order_items = OrderItemList(
                self._db_location,
                order_id=self.order_id,
                parent=self
            )
            if self.table_order_id:
                self._order_items.extend(
                    OrderItemList(
                        self._db_location,
                        order_id=self.table_order_id,
                        table_split=True,
                        parent=self
                    ))
        return self._order_items

    @property
    def payments(self):
        "Lazy-load Payment objects for this order and cache them internally"
        if self._payments is None:
            self._payments = PaymentGroup(
                self._db_location,
                payment_group_id=self.payment_group_id,
                parent=self
            )
        return self._payments

    @property
    def subtotal(self):
        """Returns the total value of all order line items minus discounts plus
        modifiers. Taxes not included"""
        return self.order_items.subtotal()

    @property
    def taxes(self):
        """Calculate order taxes based on order items and cache locally"""
        if self._taxes is None:
            with decimal.localcontext() as ctx:
                ctx.rounding = decimal.ROUND_HALF_UP
                taxes = decimal.Decimal(0.0)
                for order in self.order_items:
                    taxes += decimal.Decimal(
                        self._calc_tax_on_order_item(order))
                total = float(taxes.to_integral_value()) / 100
                self.log.debug("total tax on order: %3.2f", total)
                self._taxes = total
        return self._taxes

    @property
    def total(self):
        """Calculate the total value of the order, including taxes"""
        return self.subtotal + self.taxes

    def gross_sales_by_sales_category(self, output=None):
        """Returns a dictionary containing a subtotal of gross sales for all
        line items and modifiers, broken down by Sales Category, with keys
        being the SalesCategory object for that category, and values being
        the gross sales amounts.

        Pass in an output dictionary for cumulative totals, such as from an
        OrderTimeRange.
        """
        if output is None:
            output = dict()
        for line_item in self.order_items:
            output = line_item.gross_sales_by_sales_category(output)
        return scrub_zero_amounts(output)

    def discounts_by_sales_category(self, output=None):
        """Returns a dictionary containing a subtotal of discounts for all
        line items and modifiers, broken down by Sales Category, with keys
        being the SalesCategory object for that category, and values being
        the discount amounts.

        Pass in an output dictionary for cumulative totals, such as from an
        OrderTimeRange."""
        if output is None:
            output = dict()
        for line_item in self.order_items:
            output = line_item.discounts_by_sales_category(output)
        return scrub_zero_amounts(output)

    def net_sales_by_sales_category(self, output=None):
        """Returns a dictionary containing the subtotal of net sales broken
        down by all Sales Categories used in this order.

        Pass in an output dictionary for cumulative totals, such as from an
        OrderTimeRange."""
        if output is None:
            output = dict()
        gross = self.gross_sales_by_sales_category()
        discounts = self.discounts_by_sales_category()
        for category in gross.keys():
            output[category] = gross[category] + discounts.get(category, 0.0)
        return output

    def _calc_tax_on_order_item(self, order_item):
        """Given an OrderItem, calculate the tax on the item, in CENTS"""
        return (1 - order_item.discount_rate()) * (
            self._order_item_tax_1(order_item) +
            self._order_item_tax_2(order_item) +
            self._order_item_tax_3(order_item)) * 100

    def _order_item_tax_1(self, order_item):
        """Return the tax1 amount for a given order item"""
        return order_item.tax1_subtotal() * self.tax_rate_1

    def _order_item_tax_2(self, order_item):
        """Return the tax2 amount for a given order item"""
        taxable = order_item.tax2_subtotal()
        if self.stack_tax_2_on_tax_1:
            taxable += self._order_item_tax_1(order_item)
        return taxable * self.tax_rate_2

    def _order_item_tax_3(self, order_item):
        """Return the tax3 amount for a given order item"""
        return order_item.tax3_subtotal() * self.tax_rate_3

    def receipt_form(self):
        """Prints the order in a receipt-like format"""
        try:
            datetime = self.datetime.strftime('%Y-%m-%d %I:%M:%S %p')
        except AttributeError:
            datetime = "None"
        header = f"DETAILS FOR ORDER #{self._order_number}"
        if self.split_by > 1:
            header += f" SPLIT {self.split_number} of {self.split_by}"
        output = (
            "\n" + center(header, 47) + "\n\n"
            f"Order Date/Time:     \t{datetime}\n"
            f"Table Name: {self.table_name}\tParty: {self.party_name} "
            f"[{self.party_size} seat]\n"
            f"Bill Number: {self.bill_number}\tOrder Type: {self.order_type}\n"
            f"Server Name: {self.waiter_name}\n"
        )
        if self.custom_takeout_type:
            output += f"Takeout Type: {self.custom_takeout_type}\n"
        output += f"\n-----------------------------------------------\n\n"
        for order_item in self.order_items:
            output += order_item.receipt_form() + "\n"
        output += "\n"
        output += (
            f"-----------------------------------------------\n"
            f"                            Subtotal:  ${self.subtotal:3.2f}\n"
            f"                                 Tax:  ${self.taxes:3.2f}\n"
            f"-----------------------------------------------\n"
            f"                               TOTAL:  ${self.total:3.2f}\n"
        )
        for payment in self.payments:
            output += payment.receipt_form()
        output += "\n"
        if self.loyalty_account_name:
            output += f"Loyalty Customer: {self.loyalty_account_name}\n"
        if self.loyalty_credit_balance:
            output += (f"Loyalty Credit Balance: "
                       f"${self.loyalty_credit_balance:3.2f}\n")
        if self.loyalty_point_balance:
            output += (f"Loyalty Point Balance: "
                       f"${self.loyalty_point_balance:3.2f}\n")
        return output

    def summary(self):
        """Returns a dictionary summary of order information, such as order
        meta (time, waiter, ID), and a list of order items, including pricing,
        discounts, and modifier information.

        Output is a dict with these parent keys:

        - meta: contains a dict with order metadata
        - items: contains a list of summary dicts for each order item
        - payment: contains a dictionary of payment information for the order

        """
        output = super(PaidOrderSplit, self).summary()
        output['sales_summary'] = {
            'gross_sales_by_sales_category':
            self.gross_sales_by_sales_category(),
            'discounts_by_sales_category':
            self.discounts_by_sales_category(),
            'net_sales_by_sales_category':
            self.net_sales_by_sales_category()
        }
        output['order_items'] = self.order_items.summary()
        output['payments'] = self.payments.summary()
        # these are payment fields that are part of the base order, not from
        # ZPAYMENTS.
        loyalty_fields = [
            'loyalty_account_name', 'loyalty_credit_balance',
            'loyalty_point_balance'
        ]
        output['meta']['loyalty_info'] = dict()
        for field in loyalty_fields:
            output['meta']['loyalty_info'][field] = getattr(self, field)
        return output


class OrderItemList(TouchBistroObjectList):
    """Use this class to get a list of items for an order.
    It behaves like a sequence, where you can simply iterate over the object,
    or call it with an index to get a particular item.

    kwargs:
        - order_id
        - table_split (optional, defaults to False) set true for order items
          brought in through the ZTABLEORDER column in ZPAIDORDER.
    """
    #: The ORDERITEMS table has a version number that changes with each
    #: release. Unfortunately the version also changes column names while the
    #: structure seems to stay identical. This class variable will be
    #: incremented from the base value set below until we find a table version
    #: or run out of attempts. If we succeed, subsequent uses of the class
    #: will start at the correct version and not need subsequent attempts.
    __TBL_VERSION = 54
    #: Number of incremental attempts to get data out of this table.
    ATTEMPTS = 100

    #: This query results in a list of order item ID numbers (foreign key into
    #: the ZORDERITEM table)
    QUERY = """SELECT
            Z_{tbl_id}I_ORDERITEMS.Z_{col_id}I_ORDERITEMS AS ORDERITEM_ID
        FROM Z_{tbl_id}I_ORDERITEMS
        LEFT JOIN ZORDERITEM ON
            ZORDERITEM.Z_PK = Z_{tbl_id}I_ORDERITEMS.Z_{col_id}I_ORDERITEMS
        WHERE Z_{tbl_id}I_ORDERITEMS.Z_{tbl_id}I_ORDERS = :order_id
        ORDER BY ZORDERITEM.ZI_INDEX ASC
    """

    QUERY_BINDING_ATTRIBUTES = ['order_id']

    def subtotal(self):
        "Returns the total value of all order items after discounts/modifiers"
        amount = 0.0
        for orderitem in self.items:
            amount += orderitem.subtotal()
        return amount

    def _vivify_db_row(self, row):
        "Convert a DB row into an OrderItem"
        return OrderItem(
            self._db_location,
            order_item_id=row['ORDERITEM_ID'],
            table_split=self.kwargs.get('table_split', False),
            parent=self.parent)

    def _fetch_from_db(self):
        """Returns the db result rows for the QUERY"""
        last_err = None
        for _ in range(self.ATTEMPTS):
            try:
                query = self.QUERY.format(
                    tbl_id=OrderItemList.__TBL_VERSION,
                    col_id=OrderItemList.__TBL_VERSION + 1)
                return self.db_handle.cursor().execute(
                    query,
                    self.bindings
                ).fetchall()
            except sqlite3.OperationalError as err:
                last_err = err
            OrderItemList.__TBL_VERSION += 1
        raise last_err


class OrderItem(TouchBistroDBObject):
    """Get information about an individual order item.

    kwargs:

    - order_item_id (int) - primary key to the ZORDERITEM table.
    - table_split: if set true, assume this item is split across a table when
      determining item quantities.

    Results are a multi-column format containing details about the item.
    """

    META_ATTRIBUTES = ['quantity', 'name', 'sales_category', 'price',
                       'waiter_name', 'was_sent', 'datetime']

    QUERY = """SELECT
            ZORDERITEM.*,
            ZWAITER.ZDISPLAYNAME AS WAITERNAME,
            ZWAITER.ZUUID AS WAITER_UUID
        FROM ZORDERITEM
        LEFT JOIN ZWAITER ON
            ZWAITER.ZUUID = ZORDERITEM.ZWAITERID
        WHERE ZORDERITEM.Z_PK = :order_item_id
    """

    QUERY_BINDING_ATTRIBUTES = ['order_item_id']

    def __init__(self, db_location, **kwargs):
        super(OrderItem, self).__init__(db_location, **kwargs)
        self._table_split = kwargs.get('table_split', False)
        self._discounts = None
        self._modifiers = None
        self._menu_item = None

    @property
    def quantity(self):
        "Return the quantity associated with the order line item"
        split_by = self.parent.split_by
        if self._table_split:
            split_by = self.parent.table_split_by
        try:
            return self.db_results['ZI_QUANTITY'] / split_by
        except ZeroDivisionError:
            return 1

    @property
    def open_price(self):
        "Return the open price for the menu item (if applicable)"
        # TODO: Find orders with open items to determine how this works with
        # quantity multipliers and splits, if possible.
        return self.db_results['ZI_OPENPRICE']

    @property
    def waiter_name(self):
        "Return the customer-facing waiter name associated with the order item"
        return self.db_results['WAITERNAME']

    @property
    def course_number(self):
        """Return the course number for the menu item."""
        return self.db_results['ITEM_COURSE']

    @property
    def datetime(self):
        """Return the date and time that the item was added to the order"""
        if self.db_results['ZCREATEDATE']:
            return cocoa_2_datetime(self.db_results['ZCREATEDATE'])
        return None

    @property
    def sent_time(self):
        """Returns a Python Datetime object with local timezone corresponding
        to the time that the item was sent to the kitchen/bar (or None)"""
        if self.was_sent:
            return cocoa_2_datetime(self.db_results['ZSENTTIME'])
        return None

    @property
    def menu_item(self):
        """Return a MenuItem object corresponding to this OrderItem"""
        if self._menu_item is None:
            self._menu_item = MenuItem(
                self._db_location,
                menuitem_uuid=self.db_results['ZMENUITEMUUID'],
                parent=self)
        return self._menu_item

    @property
    def name(self):
        """Returns the name of the menu item associated with the line item"""
        return self.menu_item.name

    @property
    def sales_category(self):
        """Returns the sales category associated with this order's menu item,
        but not any of its modifiers. See sales_category_breakdown as well"""
        return self.menu_item.sales_category.name

    def gross_sales_by_sales_category(self, output=None):
        """Returns a dictionary containing a breakdown of gross sales for this
        line item split across sales categories for the base item plus all its
        modifiers and nested modifiers. Dict keys are SalesCategory objects and
        values are the gross sales for that category, for this line item"""
        if output is None:
            output = dict()
        if self.sales_category in output:
            output[self.sales_category] += self.price
        else:
            output[self.sales_category] = self.price
        for modifier in self.modifiers:
            output = modifier_sales_category_amounts(
                modifier, output=output)
        return scrub_zero_amounts(output)

    def discounts_by_sales_category(self, output=None):
        """Returns a dictionary containing a breakdown of discounts for this
        line item split across sales categories for the base item plus all its
        modifiers and nested modifiers. Dict keys are SalesCategory objects and
        values are the discount for that category, for this line item"""
        if output is None:
            output = dict()
        breakdown = self.gross_sales_by_sales_category()
        for discount in self.discounts:
            output = discount.price_by_sales_category(breakdown, output)
        return scrub_zero_amounts(output)

    def summary(self):
        """Returns a dictionary summary of this order item"""
        summary = super(OrderItem, self).summary()
        summary['menu_item'] = self.menu_item.summary()
        summary['modifiers'] = self.modifiers.summary()
        summary['discounts'] = self.discounts.summary()
        summary['taxes'] = self.tax_summary()
        return summary

    def receipt_form(self):
        """Return a receipt-formatted string for this line item, like this:

        2 x Some Menu Item Name                             $22.00
            + Some free modifier
            + $2.00: Some non-free modifier

        """
        output = ""
        name = ""
        qty = f"{self.quantity:0.2f}".rstrip('0.')
        # if self.quantity % 1 > 0.0:
        #    name += f"{self.quantity:.2f} x "
        if self.quantity != 1:
            name += f"{qty} x "
        name += self.menu_item.name
        output += "{:38s} ${:3.2f}\n".format(
            name, self.price)
        has_price_mod = False
        for modifier in self.modifiers:
            output += modifier.receipt_form()
            if modifier.price:
                has_price_mod = True
        for discount in self.discounts:
            output += "  " + discount.receipt_form()
            if discount.amount:
                has_price_mod = True
        if has_price_mod:
            output += ' ' * 23 + f"Item Subtotal:  ${self.subtotal():3.2f}\n"
        return output

    @property
    def was_sent(self):
        "Returns True if the menu item was sent to the kitchen/bar"
        if self.db_results['ZI_SENT']:
            return True
        return False

    @property
    def price(self):
        """Return the price of this line item before applying discounts and
        modifiers, taking into account quantity"""
        price = self.menu_item.price
        if self.open_price:
            price = self.open_price
        return self.quantity * price

    @property
    def gross(self):
        """Return the total value of this line item including modifiers, but
        no discounts"""
        return self.price + self.modifiers.total()

    def tax_summary(self):
        """Returns a dictionary summary of taxes for this OrderItem"""
        return {
            'tax1_subtotal': self.tax1_subtotal(),
            'tax2_subtotal': self.tax2_subtotal(),
            'tax3_subtotal': self.tax3_subtotal()
        }

    def tax1_subtotal(self):
        """Returns the amount eligible for tax1 for this order item (including
        its modifiers)."""
        taxable = 0.0
        if not self.menu_item.exclude_tax1:
            taxable += self.price
        taxable += self.modifiers.tax1_taxable_subtotal
        return taxable

    def tax2_subtotal(self):
        """Returns the amount eligible for tax2 for this order item (including
        its modifiers)."""
        taxable = 0.0
        if not self.menu_item.exclude_tax2:
            taxable += self.price
        taxable += self.modifiers.tax2_taxable_subtotal
        return taxable

    def tax3_subtotal(self):
        """Returns the amount eligible for tax3 for this order item (including
        its modifiers)."""
        taxable = 0.0
        if not self.menu_item.exclude_tax3:
            taxable += self.price
        taxable += self.modifiers.tax3_taxable_subtotal
        return taxable

    def was_voided(self):
        """Inspect discounts for this line item to see if it has a void. Voided
        items do not contribute to sales totals and have no value for reports.
        """
        for discount in self.discounts:
            if discount.is_void():
                return True
        return False

    def subtotal(self):
        """Returns the total value for the line item, by:

            - Multiplying quantity by menu item price
            - Subtracting the discount total
            - Adding any modifier pricing

        Tax is not included by default"""
        return self.gross + self.discounts.total()

    def discount_rate(self):
        """Returns a pro-rata discount rate based on the total value of all
        discounts divided by the total pre-tax value of the line item and
        its modifiers. This is used to calculate the effective tax on the line
        item after discounts. A floating point value between 0 and 1."""
        if self.discounts:
            return - self.discounts.total() / self.gross
        return 0.0

    @property
    def discounts(self):
        """Returns a list of ItemDiscount objects for this order item"""
        if self._discounts is None:
            self._discounts = ItemDiscountList(
                self._db_location,
                order_item_id=self.object_id,
                parent=self
            )
        return self._discounts

    @property
    def modifiers(self):
        """Returns a list of ItemModifier objects for this order item"""
        if self._modifiers is None:
            self._modifiers = ItemModifierList(
                self._db_location,
                order_item_id=self.object_id,
                parent=self
            )
        return self._modifiers
