"""Module to get information about orders, such as order totals, menu items,
etc.
"""
import decimal
from .base import TouchBistroDB
from .dates import cocoa_2_datetime
from .discount import ItemDiscountList
from .modifier import ItemModifierList
from .payment import Payment
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


class Order(TouchBistroDB):
    """Get detailed information about an order.

    kwargs:

    - order_number

    Results are a multi-column format containing details about the order.
    """

    META_ATTRIBUTES = [
        'order_uuid', 'order_id', 'outstanding_balance',
        'order_number', 'order_type', 'table_name',
        'bill_number', 'party_name', 'party_as_split_order',
        'custom_takeout_type', 'waiter_name', 'paid_datetime'
    ]

    #: Query to get as much information about an order as possible based on its
    #: public-facing order ID number.
    ORDER_QUERY = """SELECT
            ZORDER.Z_PK,
            ZORDER.ZPARTY, ZORDER.ZPARTYASSPLITORDER,
            ZORDER.ZCREATEDATE, ZORDER.ZI_SPLITBY, ZORDER.ZORDERNUMBER,
            ZORDER.ZUUID AS Z_ORDER_UUID, ZORDER.ZLOYALTYTRANSACTIONXREFID,
            ZORDER.ZI_EXCLUDETAX1, ZORDER.ZI_EXCLUDETAX2,
            ZORDER.ZI_EXCLUDETAX3,
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

    #: This query results in a list of order item ID numbers (foreign key into
    #: the ZORDERITEM table)
    LIST_ORDER_ITEM_QUERY = """SELECT
            Z_52I_ORDERITEMS.Z_53I_ORDERITEMS AS ORDERITEM_ID
        FROM Z_52I_ORDERITEMS
        LEFT JOIN ZORDERITEM ON
            ZORDERITEM.Z_PK = Z_52I_ORDERITEMS.Z_53I_ORDERITEMS
        WHERE Z_52I_ORDERITEMS.Z_52I_ORDERS = :z_order_id
        ORDER BY ZORDERITEM.ZI_INDEX ASC
    """

    #: This query fetches UUIDs for all payments for the paid order, in order
    #: of occurrence.
    LIST_ORDER_PAYMENT_QUERY = """SELECT
            ZUUID AS PAYMENT_UUID
        FROM ZPAYMENT
        WHERE ZPAYMENTGROUP = :payment_group_id
        ORDER BY ZI_INDEX
    """

    def __init__(self, db_location, **kwargs):
        super(Order, self).__init__(db_location, **kwargs)
        self.order_number = kwargs.get('order_number')
        self._order_items = None
        self._payments = None
        self._taxes = None

    @property
    def order_uuid(self):
        "Return the UUID for this order"
        return self.db_details['Z_ORDER_UUID']

    @property
    def order_id(self):
        "Returns the Z_PK ID for this order (not the customer-facing number)"
        return self.db_details['Z_PK']

    @property
    def bill_number(self):
        "Return the bill number for this order"
        try:
            return self.db_details['ZI_BILLNUMBER']
        except KeyError:
            return None

    @property
    def party_as_split_order(self):
        "Return the value of ZPARTYASSPLITORDER for this order"
        return self.db_details['ZPARTYASSPLITORDER']

    @property
    def party_name(self):
        "Return the party name for this order"
        try:
            return self.db_details['ZPARTYNAME']
        except KeyError:
            return None

    @property
    def table_name(self):
        "Returns the table name for the order"
        try:
            return self.db_details['ZTABLENAME']
        except KeyError:
            return None

    @property
    def paid_datetime(self):
        """Returns a Python Datetime object with local timezone corresponding
        to the time that the order was paid"""
        try:
            return cocoa_2_datetime(self.db_details['ZPAYDATE'])
        except TypeError:
            return None

    @property
    def order_type(self):
        "Returns the order type, aka 'takeout', 'dine-in', 'delivery', etc"
        try:
            return self.db_details['TAKEOUT_TYPE']
        except KeyError:
            return None

    @property
    def custom_takeout_type(self):
        "Returns the custom takeout type associated with a takeout order"
        try:
            return self.db_details['CUSTOMTAKEOUTTYPE']
        except KeyError:
            return None

    @property
    def payment_group_id(self):
        "Returns the ID for the payment group associated with this order"
        return self.db_details['ZPAYMENTS']

    @property
    def outstanding_balance(self):
        """Returns the outstanding balance amount for the order"""
        return self.db_details['ZOUTSTANDINGBALANCE']

    @property
    def loyalty_account_name(self):
        """Returns the name associated with a Loyalty account used to pay the
        order (if that was the case)"""
        return self.db_details['ZLOYALTYACCOUNTNAME']

    @property
    def loyalty_credit_balance(self):
        """Returns the credit balance of the Loyalty account used to pay the
        order (if that was the case)"""
        return self.db_details['ZLOYALTYCREDITBALANCE']

    @property
    def loyalty_point_balance(self):
        """Returns the point balance of the Loyalty account used to pay the
        order (if that was the case)"""
        return self.db_details['ZLOYALTYPOINTSBALANCE']

    @property
    def waiter_name(self):
        "Returns the display name of the waiter that closed the bill"
        try:
            return self.db_details['WAITERNAME']
        except KeyError:
            return None

    @property
    def stack_tax_2_on_tax_1(self):
        """Return True if tax 2 should be stacked on tax 1 (tax on tax)"""
        if self.db_details['ZI_TAX2ONTAX1']:
            return True
        return False

    @property
    def tax_rate_1(self):
        """Returns tax rate 1 (ZI_TAX1) column, as a decimal float"""
        return self.db_details['ZI_TAX1']

    @property
    def tax_rate_2(self):
        """Returns tax rate 2 (ZI_TAX2) column, as a decimal float"""
        return self.db_details['ZI_TAX2']

    @property
    def tax_rate_3(self):
        """Returns tax rate 3 (ZI_TAX3) column, as a decimal float"""
        return self.db_details['ZI_TAX3']

    @property
    def order_items(self):
        "Lazy-load order items on the first attempt to read them, then cache"
        if self._order_items is None:
            self._order_items = list()
            for row in self._fetch_order_items():
                self._order_items.append(
                    OrderItem(
                        self._db_location,
                        order_item_id=row['ORDERITEM_ID']))
        return self._order_items

    @property
    def payments(self):
        "Lazy-load Payment objects for this order and cache them internally"
        if self._payments is None:
            self._payments = list()
            for row in self._fetch_payments():
                self._payments.append(
                    Payment(
                        self._db_location,
                        payment_uuid=row['PAYMENT_UUID'])
                )
        return self._payments

    def subtotal(self):
        """Returns the total value of all order line items minus discounts plus
        modifiers. Taxes not included"""
        total = 0.0
        for order in self.order_items:
            total += order.subtotal()
        return total

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

    def total(self):
        """Calculate the total value of the order, including taxes"""
        return self.subtotal() + self.taxes()

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
            datetime = self.paid_datetime.strftime('%Y-%m-%d %I:%M:%S %p')
        except AttributeError:
            datetime = "None"
        output = (
            f"\n       ORDER DETAILS FOR ORDER #{self.order_number}\n\n"
            f"Order Date/Time:     \t{datetime}\n"
            f"Table Name: {self.table_name}\tParty Name: {self.party_name}\n"
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
            f"                            Subtotal:  ${self.subtotal():3.2f}\n"
            f"                                 Tax:  ${self.taxes():3.2f}\n"
            f"-----------------------------------------------\n"
            f"                               TOTAL:  ${self.total():3.2f}\n"
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
        self.log.debug(output)
        output['order_items'] = list()
        output['payments'] = list()
        for orderitem in self.order_items:
            output['order_items'].append(orderitem.summary())
        for payment in self.payments:
            output['payments'].append(payment.summary())
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

    def _fetch_entry(self):
        """Returns a summary list of dicts as per the class summary"""
        bindings = {
            'order_number': self.order_number}
        return self.db_handle.cursor().execute(
            self.ORDER_QUERY, bindings).fetchone()

    def _fetch_order_items(self):
        """Returns an iterable of database results for order items associated
        with this order"""
        bindings = {
            'z_order_id': self.order_id}
        return self.db_handle.cursor().execute(
            self.LIST_ORDER_ITEM_QUERY, bindings).fetchall()

    def _fetch_payments(self):
        """Returns an iterable of database results for payments associated
        with this order"""
        bindings = {
            'payment_group_id': self.payment_group_id}
        return self.db_handle.cursor().execute(
            self.LIST_ORDER_PAYMENT_QUERY, bindings).fetchall()


class OrderItem(TouchBistroDB):
    """Get information about an individual order item.

    kwargs:

    - order_item_id (int) - primary key to the ZORDERITEM table.

    Results are a multi-column format containing details about the item.
    """

    META_ATTRIBUTES = ['order_item_id', 'quantity',
                       'open_price', 'waiter_name', 'was_sent', 'sent_time']

    QUERY = """SELECT
            ZORDERITEM.ZMENUITEMUUID,
            ZORDERITEM.ZI_QUANTITY, ZORDERITEM.ZI_OPENPRICE,
            ZWAITER.ZDISPLAYNAME AS WAITERNAME,
            ZWAITER.ZUUID AS WAITER_UUID,
            ZORDERITEM.ZI_COURSE AS ITEM_COURSE,
            ZORDERITEM.ZI_SENT, ZORDERITEM.ZSENTTIME
        FROM ZORDERITEM
        LEFT JOIN ZWAITER ON
            ZWAITER.ZUUID = ZORDERITEM.ZWAITERID
        WHERE ZORDERITEM.Z_PK = :order_item_id
    """

    def __init__(self, db_location, **kwargs):
        super(OrderItem, self).__init__(db_location, **kwargs)
        self.order_item_id = kwargs.get('order_item_id')
        self._discounts = None
        self._modifiers = None
        self._menu_item = None

    @property
    def quantity(self):
        "Return the quantity associated with the order line item"
        return self.db_details['ZI_QUANTITY']

    @property
    def open_price(self):
        "Return the open price for the menu item (if applicable)"
        return self.db_details['ZI_OPENPRICE']

    @property
    def waiter_name(self):
        "Return the customer-facing waiter name associated with the order item"
        return self.db_details['WAITERNAME']

    @property
    def course_number(self):
        """Return the course number for the menu item."""
        return self.db_details['ITEM_COURSE']

    @property
    def sent_time(self):
        """Returns a Python Datetime object with local timezone corresponding
        to the time that the item was sent to the kitchen/bar (or None)"""
        if self.was_sent:
            return cocoa_2_datetime(self.db_details['ZSENTTIME'])
        return None

    @property
    def menu_item(self):
        """Return a MenuItem object corresponding to this OrderItem"""
        if self._menu_item is None:
            self._menu_item = MenuItem(
                self._db_location,
                menuitem_uuid=self.db_details['ZMENUITEMUUID'])
        return self._menu_item

    def summary(self):
        """Returns a dictionary summary of this order item"""
        summary = super(OrderItem, self).summary()
        summary['modifiers'] = list()
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
            name += f"{self.quantity} x "
        name += self.menu_item.name
        output += "{:38s} ${:3.2f}\n".format(
            name, self.base_price())
        has_price_mod = False
        for modifier in self.modifiers:
            output += "  " + modifier.receipt_form()
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
        if self.db_details['ZI_SENT']:
            return True
        return False

    def base_price(self):
        """Return the price of this line item before applying discounts and
        modifiers, taking into account quantity"""
        price = self.menu_item.price
        if self.open_price:
            price = self.open_price
        return self.quantity * price

    def subtotal(self):
        """Returns the total value for the line item, by:

            - Multiplying quantity by menu item price
            - Subtracting the discount total
            - Adding any modifier pricing

        Tax is not included by default"""
        amount = self.base_price()
        amount -= self.discounts.total()
        amount += self.modifiers.total()
        return amount

    @property
    def discounts(self):
        """Returns a list of ItemDiscount objects for this order item"""
        if self._discounts is None:
            self._discounts = ItemDiscountList(
                self._db_location,
                order_item_id=self.order_item_id)
        return self._discounts

    @property
    def modifiers(self):
        """Returns a list of ItemModifier objects for this order item"""
        if self._modifiers is None:
            self._modifiers = ItemModifierList(
                self._db_location,
                order_item_id=self.order_item_id
            )
        return self._modifiers

    def _fetch_entry(self):
        """Returns a summary list of dicts as per the class summary"""
        bindings = {
            'order_item_id': self.order_item_id}
        return self.db_handle.cursor().execute(
            self.QUERY, bindings
        ).fetchone()
