"""Module to get information about orders, such as order totals, menu items,
etc.
"""
import logging
from lib7shifts.cmd.common import Sync7Shifts2Sqlite
from .dates import cocoa_2_datetime


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
            ZORDER.ZBILLNUMBER, ZORDER.ZPARTY, ZORDER.ZPARTYASSPLITORDER,
            ZORDER.ZCREATEDATE, ZORDER.ZI_SPLITBY, ZORDER.ZORDERNUMBER,
            ZORDER.ZUUID AS Z_ORDER_UUID, ZORDER.ZLOYALTYTRANSACTIONXREFID,
            ZORDER.ZI_EXCLUDETAX1, ZORDER.ZI_EXCLUDETAX2,
            ZORDER.ZI_EXCLUDETAX3,
            ZPAIDORDER.ZPAYDATE,
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
            ZPAIDORDER.ZPAYMENTS, ZWAITER.ZDISPLAYNAME AS WAITERNAME,
            ZPAYMENT.ZCARDTYPE,
            ZCUSTOMTAKEOUTTYPE.ZNAME as CUSTOMTAKEOUTTYPE,
            ifnull(round(ZPAYMENT.ZI_AMOUNT, 2), 0.0) as ZI_AMOUNT,
            ifnull(round(ZPAYMENT.ZTIP, 2), 0.0) as ZTIP
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
        self._order_info = None
        self._order_items = None

    @property
    def order_info(self):
        "Lazy-load order info from DB on first request, cache it after that"
        if self._order_info is None:
            self._order_info = dict()
            result = self._fetch_order()
            for key in result.keys():
                self._order_info[key] = result[key]
        return self._order_info

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
            'z_order_id': self.order_info['Z_PK']}
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

    def __init__(self, db_location, **kwargs):
        super(OrderItem, self).__init__(db_location, **kwargs)
        self.log = logging.getLogger("{}.{}".format(
            self.__class__.__module__, self.__class__.__name__
        ))
        self.order_item_id = kwargs.get('order_item_id')
        self._db_details = None

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

    def was_sent(self):
        "Returns True if the menu item was sent to the kitchen/bar"
        if self.db_details['ZI_SENT']:
            return True
        return False

    @property
    def db_details(self):
        "Fetch/Cache and Return the database results for this order item ID"
        if self._db_details is None:
            self._db_details = dict()
            result = self._fetch_order_item()
            for key in result.keys():
                self._db_details[key] = result[key]
        return self._db_details

    def _fetch_order_item(self):
        """Returns a summary list of dicts as per the class summary"""
        bindings = {
            'order_item_id': self.order_item_id}
        return self.db_handle.cursor().execute(
            self.QUERY, bindings
        ).fetchone()

    def __str__(self):
        "Provide a nice string representation of the Order Item"
        return(
            f"OrderItem(\n"
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
