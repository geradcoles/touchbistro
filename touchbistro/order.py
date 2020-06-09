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


def takeout_type_pretty(value):
    "Returns a friendly takeout type from a mapped value"
    return ZI_TAKEOUTTYPE_MAP[value]


ZI_TAKEOUTTYPE_MAP = {
    None: 'dinein',
    0: 'takeout',
    1: 'delivery',
    2: 'bartab'
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


class Order(TouchBistroDBObject):
    """Get detailed information about an order.

    kwargs:

    - order_number

    Results are a multi-column format containing details about the order.
    """

    META_ATTRIBUTES = [
        'outstanding_balance',
        'order_number', 'order_type', 'table_name',
        'bill_number', 'party_name', 'party_as_split_order',
        'custom_takeout_type', 'waiter_name', 'datetime',
        'subtotal', 'taxes', 'total', 'party_size',
    ]

    #: Query to get as much information about an order as possible based on its
    #: public-facing order ID number.
    QUERY = """SELECT
            ZORDER.*,
            ZPAIDORDER.ZPAYDATE, ZPAIDORDER.ZI_BILLNUMBER,
            ZPAIDORDER.ZI_GRATUITYBEFORETAX, ZPAIDORDER.ZI_GRATUITY,
            ZPAIDORDER.ZI_TAX2ONTAX1,
            ZPAIDORDER.ZI_REDUCEDTAX1, ZPAIDORDER.ZI_REDUCEDTAX1BILLAMOUNT,
            ZPAIDORDER.ZI_REDUCEDTAX2, ZPAIDORDER.ZI_REDUCEDTAX2BILLAMOUNT,
            ZPAIDORDER.ZI_REDUCEDTAX3, ZPAIDORDER.ZI_REDUCEDTAX3BILLAMOUNT,
            ZPAIDORDER.ZI_TAX1, ZPAIDORDER.ZI_TAX2, ZPAIDORDER.ZI_TAX3,
            ZPAIDORDER.ZLOYALTYCREDITBALANCE, ZPAIDORDER.ZLOYALTYPOINTSBALANCE,
            ZPAIDORDER.ZOUTSTANDINGBALANCE, ZPAIDORDER.ZLOYALTYACCOUNTNAME,
            ZPAIDORDER.ZPARTYNAME, ZPAIDORDER.ZTABLENAME,
            ZPAIDORDER.ZI_GROUPNUMBER,
            ZPAIDORDER.ZI_PARTYSIZE, ZPAIDORDER.ZI_SPLIT,
            CASE ZPAIDORDER.ZI_TAKEOUTTYPE
                WHEN 2
                    THEN 'bartab'
                WHEN 1
                    THEN 'delivery'
                WHEN 0
                    THEN 'takeout'
                ELSE 'dinein'
            END TAKEOUT_TYPE,
            ZPAIDORDER.ZBILLRANGE, ZPAIDORDER.ZCLOSEDTAKEOUT,
            ZPAIDORDER.ZPAYMENTS,
            ZWAITER.ZDISPLAYNAME AS WAITERNAME,
            ZWAITER.ZUUID AS WAITER_UUID,
            ZCUSTOMTAKEOUTTYPE.ZNAME as CUSTOMTAKEOUTTYPE
        FROM ZORDER
        LEFT JOIN ZPAIDORDER ON
            ZPAIDORDER.Z_PK = ZORDER.ZPAIDORDER
        LEFT JOIN ZCLOSEDTAKEOUT ON
            ZCLOSEDTAKEOUT.Z_PK = ZPAIDORDER.ZCLOSEDTAKEOUT
        LEFT JOIN ZCUSTOMTAKEOUTTYPE ON
            ZCUSTOMTAKEOUTTYPE.Z_PK = ZCLOSEDTAKEOUT.ZCUSTOMTAKEOUTTYPE
        LEFT JOIN ZWAITER ON
            ZWAITER.ZUUID = ZPAIDORDER.ZWAITERUUID
        WHERE ZORDER.ZORDERNUMBER = :order_number
        ORDER BY ZORDER.Z_PK DESC LIMIT 1 /* there can be more than 1 */
    """
    # TODO: the LIMIT 1 is surely a problem that is leading to an oversight of
    # some sort. Investigate why there are sometimes more than 1 row.

    QUERY_BINDING_ATTRIBUTES = ['order_number']

    def __init__(self, db_location, **kwargs):
        super(Order, self).__init__(db_location, **kwargs)
        self._order_items = None
        self._payments = None
        self._taxes = None

    @property
    def order_number(self):
        "Return the order number for this order"
        return self.db_results['ZORDERNUMBER']

    @property
    def bill_number(self):
        "Return the bill number for this order"
        try:
            return self.db_results['ZI_BILLNUMBER']
        except KeyError:
            return None

    @property
    def party_as_split_order(self):
        "Return the value of ZPARTYASSPLITORDER for this order"
        return self.db_results['ZPARTYASSPLITORDER']

    @property
    def party_name(self):
        "Return the party name for this order"
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
    def datetime(self):
        """Returns a Python Datetime object with local timezone corresponding
        to the time that the order was paid"""
        try:
            return cocoa_2_datetime(self.db_results['ZPAYDATE'])
        except TypeError:
            return None

    @property
    def order_type(self):
        "Returns the order type, aka 'takeout', 'dine-in', 'delivery', etc"
        try:
            return self.db_results['TAKEOUT_TYPE']
        except KeyError:
            return None

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
    def waiter_name(self):
        "Returns the display name of the waiter that closed the bill"
        try:
            return self.db_results['WAITERNAME']
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
                order_id=self.object_id
            )
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
                    taxes += self._calc_tax_on_order_item(order)
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
        tax1 = decimal.Decimal(0.0)
        tax2 = decimal.Decimal(0.0)
        tax3 = decimal.Decimal(0.0)
        # work in cents to avoid penny rounding problems.
        order_subtotal = decimal.Decimal(order_item.subtotal() * 100)
        if not order_item.menu_item.exclude_tax1:
            tax1 += order_subtotal * decimal.Decimal(self.tax_rate_1)
        if not order_item.menu_item.exclude_tax2:
            taxable = order_subtotal
            if self.stack_tax_2_on_tax_1:
                taxable += tax1
            tax2 += taxable * decimal.Decimal(self.tax_rate_2)
        if not order_item.menu_item.exclude_tax3:
            tax3 += order_subtotal * decimal.Decimal(self.tax_rate_3)
        return tax1 + tax2 + tax3

    def receipt_form(self):
        """Prints the order in a receipt-like format"""
        try:
            datetime = self.datetime.strftime('%Y-%m-%d %I:%M:%S %p')
        except AttributeError:
            datetime = "None"
        output = (
            f"\n       DETAILS FOR ORDER #{self.order_number}\n\n"
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
        output = super(Order, self).summary()
        output['gross_sales_by_sales_category'] = \
            self.gross_sales_by_sales_category()
        output['discounts_by_sales_category'] = \
            self.discounts_by_sales_category()
        output['net_sales_by_sales_category'] = \
            self.net_sales_by_sales_category()
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


class OrderFromId(Order):
    """Get detailed information about an order based on its ID number
    (not the order number - be careful - this is the Z_PK column)

    kwargs:

    - order_id
    """
    QUERY = """SELECT
        ZORDER.*,
        ZPAIDORDER.ZPAYDATE, ZPAIDORDER.ZI_BILLNUMBER,
        ZPAIDORDER.ZI_GRATUITYBEFORETAX, ZPAIDORDER.ZI_GRATUITY,
        ZPAIDORDER.ZI_TAX2ONTAX1,
        ZPAIDORDER.ZI_REDUCEDTAX1, ZPAIDORDER.ZI_REDUCEDTAX1BILLAMOUNT,
        ZPAIDORDER.ZI_REDUCEDTAX2, ZPAIDORDER.ZI_REDUCEDTAX2BILLAMOUNT,
        ZPAIDORDER.ZI_REDUCEDTAX3, ZPAIDORDER.ZI_REDUCEDTAX3BILLAMOUNT,
        ZPAIDORDER.ZI_TAX1, ZPAIDORDER.ZI_TAX2, ZPAIDORDER.ZI_TAX3,
        ZPAIDORDER.ZLOYALTYCREDITBALANCE, ZPAIDORDER.ZLOYALTYPOINTSBALANCE,
        ZPAIDORDER.ZOUTSTANDINGBALANCE, ZPAIDORDER.ZLOYALTYACCOUNTNAME,
        ZPAIDORDER.ZPARTYNAME, ZPAIDORDER.ZTABLENAME,
        ZPAIDORDER.ZI_GROUPNUMBER,
        ZPAIDORDER.ZI_PARTYSIZE, ZPAIDORDER.ZI_SPLIT,
        CASE ZPAIDORDER.ZI_TAKEOUTTYPE
            WHEN 2
                THEN 'bartab'
            WHEN 1
                THEN 'delivery'
            WHEN 0
                THEN 'takeout'
            ELSE 'dinein'
        END TAKEOUT_TYPE,
        ZPAIDORDER.ZBILLRANGE, ZPAIDORDER.ZCLOSEDTAKEOUT,
        ZPAIDORDER.ZPAYMENTS,
        ZWAITER.ZDISPLAYNAME AS WAITERNAME,
        ZWAITER.ZUUID AS WAITER_UUID,
        ZCUSTOMTAKEOUTTYPE.ZNAME as CUSTOMTAKEOUTTYPE
    FROM ZORDER
    LEFT JOIN ZPAIDORDER ON
        ZPAIDORDER.Z_PK = ZORDER.ZPAIDORDER
    LEFT JOIN ZCLOSEDTAKEOUT ON
        ZCLOSEDTAKEOUT.Z_PK = ZPAIDORDER.ZCLOSEDTAKEOUT
    LEFT JOIN ZCUSTOMTAKEOUTTYPE ON
        ZCUSTOMTAKEOUTTYPE.Z_PK = ZCLOSEDTAKEOUT.ZCUSTOMTAKEOUTTYPE
    LEFT JOIN ZWAITER ON
        ZWAITER.ZUUID = ZPAIDORDER.ZWAITERUUID
    WHERE ZORDER.Z_PK = :order_id
    ORDER BY ZORDER.Z_PK DESC LIMIT 1
    """

    QUERY_BINDING_ATTRIBUTES = ['order_id']


class OrderItemList(TouchBistroObjectList):
    """Use this class to get a list of items for an order.
    It behaves like a sequence, where you can simply iterate over the object,
    or call it with an index to get a particular item.

    kwargs:
        - order_id
    """
    #: The ORDERITEMS table has a version number that changes with each
    #: release. Unfortunately the version also changes column names while the
    #: structure seems to stay identical.
    BASE_ID = 54
    #: Number of incremental attempts to get data out of this table.
    ATTEMPTS = 20

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
            self._db_location, order_item_id=row['ORDERITEM_ID'])

    def _fetch_from_db(self):
        """Returns the db result rows for the QUERY"""
        last_err = None
        for offset in range(self.ATTEMPTS):
            try:
                tbl_id = self.BASE_ID + offset
                col_id = tbl_id + 1
                return self.db_handle.cursor().execute(
                    self.QUERY.format(
                        tbl_id=tbl_id, col_id=col_id), self.bindings
                ).fetchall()
            except sqlite3.OperationalError as err:
                last_err = err
        raise last_err


class OrderItem(TouchBistroDBObject):
    """Get information about an individual order item.

    kwargs:

    - order_item_id (int) - primary key to the ZORDERITEM table.

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
        self._discounts = None
        self._modifiers = None
        self._menu_item = None

    @property
    def quantity(self):
        "Return the quantity associated with the order line item"
        return self.db_results['ZI_QUANTITY']

    @property
    def open_price(self):
        "Return the open price for the menu item (if applicable)"
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
        return summary

    def receipt_form(self):
        """Return a receipt-formatted string for this line item, like this:

        2 x Some Menu Item Name                             $22.00
            + Some free modifier
            + $2.00: Some non-free modifier

        """
        output = ""
        name = ""
        if self.quantity > 1:
            name += f"{self.quantity:.0f} x "
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
