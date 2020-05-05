"""Module to get information about orders, such as order totals, menu items,
etc.
"""
import logging
from lib7shifts.cmd.common import Sync7Shifts2Sqlite
from .dates import cocoa_2_datetime
from .discount import ItemDiscount
from .modifier import ItemModifier


def takeout_type_pretty(value):
    "Returns a friendly takeout type from a mapped value"
    return ZI_TAKEOUTTYPE_MAP[value]


ZI_TAKEOUTTYPE_MAP = {
    None: 'dinein',
    0: 'takeout',
    1: 'delivery',
    2: 'bartab'
}


class Order(Sync7Shifts2Sqlite):
    """Get detailed information about an order.

    kwargs:

    - order_number

    Results are a multi-column format containing details about the order.
    """

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
            ZPAYMENT.ZCARDTYPE,
            ZPAYMENT.ZAUTH,
            ZCUSTOMTAKEOUTTYPE.ZNAME as CUSTOMTAKEOUTTYPE,
            ifnull(round(ZPAYMENT.ZI_AMOUNT, 2), 0.0) as ZI_PAYMENT_AMOUNT,
            ifnull(round(ZPAYMENT.ZTIP, 2), 0.0) as ZTIP_AMOUNT
        FROM ZORDER
        LEFT JOIN ZPAIDORDER ON
            ZPAIDORDER.Z_PK = ZORDER.ZPAIDORDER
        LEFT JOIN ZPAYMENT ON
            ZPAYMENT.ZPAYMENTGROUP = ZPAIDORDER.ZPAYMENTS
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

    def __init__(self, db_location, **kwargs):
        super(Order, self).__init__(db_location, **kwargs)
        self.log = logging.getLogger("{}.{}".format(
            self.__class__.__module__, self.__class__.__name__
        ))
        self.order_number = kwargs.get('order_number')
        self._db_details = None
        self._order_items = None

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
        return self.db_details['ZI_BILLNUMBER']

    @property
    def party_as_split_order(self):
        "Return the value of ZPARTYASSPLITORDER for this order"
        return self.db_details['ZPARTYASSPLITORDER']

    @property
    def party_name(self):
        "Return the party name for this order"
        return self.db_details['ZPARTYNAME']

    @property
    def table_name(self):
        "Returns the table name for the order"
        return self.db_details['ZTABLENAME']

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
        return self.db_details['TAKEOUT_TYPE']

    @property
    def custom_takeout_type(self):
        "Returns the custom takeout type associated with a takeout order"
        return self.db_details['CUSTOMTAKEOUTTYPE']

    @property
    def payment_amount(self):
        """Returns the payment amount for paid orders"""
        return self.db_details['ZI_PAYMENT_AMOUNT']

    @property
    def tip_amount(self):
        """Returns the tip amount for paid orders"""
        return self.db_details['ZTIP_AMOUNT']

    @property
    def outstanding_balance(self):
        """Returns the outstanding balance amount for the order"""
        return self.db_details['ZOUTSTANDINGBALANCE']

    @property
    def card_type(self):
        """When payment cards are used, return the card type"""
        return self.db_details['ZCARDTYPE']

    @property
    def auth_number(self):
        """When payment cards are used, return the card authorization #"""
        return self.db_details['ZAUTH']

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
        return self.db_details['WAITERNAME']

    @property
    def db_details(self):
        "Lazy-load order info from DB on first request, cache it after that"
        if self._db_details is None:
            self._db_details = dict()
            result = self._fetch_order()
            for key in result.keys():
                self._db_details[key] = result[key]
        return self._db_details

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

    def subtotal(self):
        """Returns the total value of all order line items minus discounts plus
        modifiers. Taxes not included"""
        total = 0.0
        for order in self.order_items:
            total += order.subtotal()
        return total

    def receipt_form(self):
        """Prints the order in a receipt-like format"""
        datetime = self.paid_datetime.strftime('%Y-%m-%d %I:%M:%S %p')
        output = (
            f"        ORDER DETAILS FOR ORDER #{self.order_number}\n\n"
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
        subtotal = self.subtotal()
        output += (
            f"-----------------------------------------------\n"
            f"                            Subtotal:  ${subtotal:3.2f}\n"
            f"                                 Tax:  TODO\n"
            f"-----------------------------------------------\n"
            f"                               TOTAL:  ${subtotal:3.2f}\n"
            f"                            Gratuity:  "
            f"${self.tip_amount:3.2f}\n"
            f"                      Payment Amount:  "
            f"${self.payment_amount:3.2f}\n"
            f"                 Outstanding Balance:  "
            f"${self.outstanding_balance:3.2f}\n"
        )
        if self.card_type:
            output += ("                           Card Type:  "
                       f"{self.card_type.upper()}\n")
        if self.loyalty_credit_balance:
            output += (f"              Loyalty Credit Balance:  "
                       "${self.loyalty_credit_balance:3.2f}\n")
        if self.loyalty_point_balance:
            output += (f"               Loyalty Point Balance:  "
                       "${self.loyalty_point_balance:3.2f}\n")
        output += "\n"
        if self.loyalty_account_name:
            output += f"Loyalty Customer: {self.loyalty_account_name}\n"
        if self.auth_number:
            output += f"Auth #: {self.auth_number}\n"
        output += "\n"
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
        output = {'meta': dict(), 'order_items': list(), 'payment': dict()}
        meta_fields = [
            'order_uuid',
            'order_number', 'order_type', 'table_name',
            'bill_number', 'party_name', 'party_as_split_order',
            'custom_takeout_type',
        ]
        for field in meta_fields:
            output['meta'][field] = getattr(self, field)
        payment_fields = [
            'paid_datetime', 'loyalty_account_name', 'loyalty_credit_balance',
            'loyalty_point_balance', 'outstanding_balance', 'card_type',
            'waiter_name', 'payment_amount', 'tip_amount', 'auth_number'
        ]
        for field in payment_fields:
            output['payment'][field] = getattr(self, field)
        for orderitem in self.order_items:
            output['order_items'].append(orderitem.summary())
        return output

    def _fetch_order(self):
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


class OrderItem(Sync7Shifts2Sqlite):
    """Get information about an individual order item.

    kwargs:

    - order_item_id (int) - primary key to the ZORDERITEM table.

    Results are a multi-column format containing details about the item.
    """

    QUERY = """SELECT
        ZMENUITEM.ZNAME, ZMENUITEM.ZCATEGORYNAME AS ITEM_MENU_CATEGORY_NAME,
        ZMENUCATEGORY.ZNAME AS MENU_CATEGORY_NAME,
        ZITEMTYPE.ZNAME AS SALES_CATEGORY_NAME,
        ZMENUCATEGORY.ZI_TAX1 AS MENU_CATEGORY_TAX1,
        ZMENUCATEGORY.ZI_TAX2 AS MENU_CATEGORY_TAX2,
        ZMENUCATEGORY.ZI_TAX3 AS MENU_CATEGORY_TAX3,
        ZORDERITEM.ZI_QUANTITY, ZMENUITEM.ZI_PRICE, ZORDERITEM.ZI_OPENPRICE,
        ZWAITER.ZDISPLAYNAME AS WAITERNAME,
        ZWAITER.ZUUID AS WAITER_UUID,
        ZORDERITEM.ZI_COURSE AS ITEM_COURSE,
        ZMENUCATEGORY.ZI_COURSE AS MENU_CATEGORY_COURSE,
        ZORDERITEM.ZI_SENT, ZORDERITEM.ZSENTTIME
        FROM ZORDERITEM
        LEFT JOIN ZMENUITEM ON
            ZMENUITEM.ZUUID = ZORDERITEM.ZMENUITEMUUID
        LEFT JOIN ZMENUCATEGORY ON
            ZMENUCATEGORY.ZUUID = ZMENUITEM.ZCATEGORYUUID
        LEFT JOIN ZITEMTYPE ON
            ZITEMTYPE.ZTYPEID = ZMENUITEM.ZTYPE
        LEFT JOIN ZWAITER ON
            ZWAITER.ZUUID = ZORDERITEM.ZWAITERID
        WHERE ZORDERITEM.Z_PK = :order_item_id
    """

    #: Query to get a list of discount PK's for this order item
    DISCOUNT_QUERY = """SELECT
        ZUUID
        FROM ZDISCOUNT
        WHERE ZORDERITEM = :order_item_id
        ORDER BY ZI_INDEX ASC
        """

    #: Query to get a list of modifier UUID's for this order item
    MODIFIER_QUERY = """SELECT
        ZUUID
        FROM ZMODIFIER
        WHERE ZCONTAINERORDERITEM = :order_item_id
        ORDER BY ZI_INDEX ASC
        """

    def __init__(self, db_location, **kwargs):
        super(OrderItem, self).__init__(db_location, **kwargs)
        self.log = logging.getLogger("{}.{}".format(
            self.__class__.__module__, self.__class__.__name__
        ))
        self.order_item_id = kwargs.get('order_item_id')
        self._db_details = None
        self._discounts = None
        self._modifiers = None

    @property
    def name(self):
        "Map to the appropriate DB result column for menu item name"
        return self.db_details['ZNAME']

    @property
    def sales_category_name(self):
        "Map to the appropriate DB result column for sales category name"
        return self.db_details['SALES_CATEGORY_NAME']

    @property
    def menu_category_name(self):
        "Map to the appropriate DB result column for menu category name"
        return self.db_details['ITEM_MENU_CATEGORY_NAME']

    @property
    def quantity(self):
        "Return the quantity associated with the order line item"
        return self.db_details['ZI_QUANTITY']

    @property
    def original_price(self):
        "Return the pre-discount price of the menu item (tax-excluded)"
        return self.db_details['ZI_PRICE']

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
        if self.db_details['ITEM_COURSE'] >= 0:
            return self.db_details['ITEM_COURSE']
        return self.db_details['MENU_CATEGORY_COURSE']

    @property
    def sent_time(self):
        """Returns a Python Datetime object with local timezone corresponding
        to the time that the item was sent to the kitchen/bar (or None)"""
        if self.was_sent():
            return cocoa_2_datetime(self.db_details['ZSENTTIME'])
        return None

    def summary(self):
        """Returns a dictionary summary of this order item"""
        summary = {
            'meta': dict(), 'modifiers': list(), 'discounts': list()}
        fields = ['order_item_id', 'name', 'menu_category_name',
                  'sales_category_name', 'quantity', 'original_price',
                  'open_price', 'waiter_name', 'course_number', 'sent_time']
        for field in fields:
            summary['meta'][field] = getattr(self, field)
        for modifier in self.get_modifiers():
            summary['modifiers'].append(modifier.summary())
        for discount in self.get_discounts():
            summary['discounts'].append(discount.summary())
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
        name += self.name
        output += "{:38s} ${:3.2f}\n".format(
            name, self.subtotal())
        for discount in self.get_discounts():
            output += "  " + discount.receipt_form()
        for modifier in self.get_modifiers():
            output += "  " + modifier.receipt_form()
        return output

    def was_sent(self):
        "Returns True if the menu item was sent to the kitchen/bar"
        if self.db_details['ZI_SENT']:
            return True
        return False

    def subtotal(self):
        """Returns the total value for the line item, by:

            - Multiplying quantity by menu item price
            - Subtracting the discount total
            - Adding any modifier pricing

        Tax is not included by default"""
        price = self.original_price
        if self.open_price:
            price = self.open_price
        amount = self.quantity * price
        amount -= self.discount_total()
        amount += self.modifier_total()
        return amount

    @property
    def db_details(self):
        "Fetch/Cache and Return the database results for this order item ID"
        if self._db_details is None:
            self._db_details = dict()
            result = self._fetch_order_item()
            for key in result.keys():
                self._db_details[key] = result[key]
        return self._db_details

    def get_discounts(self):
        """Returns a list of ItemDiscount objects for this order item"""
        if self._discounts is None:
            self._discounts = list()
            for row in self._fetch_discounts():
                self._discounts.append(
                    ItemDiscount(self._db_location,
                                 discount_uuid=row['ZUUID']))
        return self._discounts

    def get_modifiers(self):
        """Returns a list of ItemModifier objects for this order item"""
        if self._modifiers is None:
            self._modifiers = list()
            for row in self._fetch_modifiers():
                self._modifiers.append(
                    ItemModifier(self._db_location,
                                 modifier_uuid=row['ZUUID']))
        return self._modifiers

    def discount_total(self):
        """Returns the total discounted amount for this Order Item"""
        amount = 0.0
        for discount in self.get_discounts():
            amount += discount.amount
        return amount

    def modifier_total(self):
        "Returns the total value of all modifiers applied to this item"
        amount = 0.0
        for modifier in self.get_modifiers():
            amount += modifier.price
        return amount

    def _fetch_order_item(self):
        """Returns a summary list of dicts as per the class summary"""
        bindings = {
            'order_item_id': self.order_item_id}
        return self.db_handle.cursor().execute(
            self.QUERY, bindings
        ).fetchone()

    def _fetch_discounts(self):
        """Returns a list of discount uuids from the DB for this order
        item"""
        bindings = {
            'order_item_id': self.order_item_id}
        return self.db_handle.cursor().execute(
            self.DISCOUNT_QUERY, bindings
        ).fetchall()

    def _fetch_modifiers(self):
        """Returns a list of modifier uuids from the DB for this order
        item"""
        bindings = {
            'order_item_id': self.order_item_id}
        return self.db_handle.cursor().execute(
            self.MODIFIER_QUERY, bindings
        ).fetchall()

    def __str__(self):
        "Provide a nice string representation of the Order Item"
        return(
            f"OrderItem(\n"
            f"  order_item_id: {self.order_item_id}\n"
            f"  name: {self.name}\n"
            f"  menu_category_name: {self.menu_category_name}\n"
            f"  sales_category_name: {self.sales_category_name}\n"
            f"  quantity: {self.quantity}\n"
            f"  original_price: {self.original_price}\n"
            f"  open_price: {self.open_price}\n"
            f"  waiter_name: {self.waiter_name}\n"
            f"  course_number: {self.course_number}\n"
            f"  sent_time: {self.sent_time}\n"
            ")"
        )
