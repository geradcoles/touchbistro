"""This module contains classes and functions to work with TouchBistro
payments.
"""
from .base import TouchBistroDBObject, TouchBistroObjectList
from .dates import cocoa_2_datetime


#: This map is used to generate a human-readable name for ZI_TYPE in the
#: ZPAYMENT table.
PAYMENT_TYPES = ("Cash", "Electronic", "Unknown", "Unknown", "Unknown",
                 "Customer Account")


def payment_type_name(type_id):
    "Given a payment type id, return a payment type name from PAYMENT_TYPES"
    return PAYMENT_TYPES[type_id]


class PaymentGroup(TouchBistroObjectList):
    """Use this class to get a list of Payment objects for a payment group.
    It behaves like a sequence, where you can simply iterate over the object,
    or call it with an index to get a particular item.

    kwargs:
        - payment_group_id
    """

    #: Query to get a list of modifier uuids for this order item
    QUERY = """SELECT
            ZUUID
        FROM ZPAYMENT
        WHERE ZPAYMENTGROUP = :payment_group_id
        ORDER BY ZI_INDEX ASC
        """

    def total_amount(self):
        "Returns the total value of payments in the list"
        amount = 0.0
        for payment in self.items:
            amount += payment.amount
        return amount

    @property
    def items(self):
        "Returns the discounts as a list, caching db results"
        if self._items is None:
            self._items = list()
            for row in self._fetch_items():
                self._items.append(
                    Payment(
                        self._db_location,
                        payment_uuid=row['ZUUID']))
        return self._items

    def _fetch_items(self):
        """Returns a list of payments from the DB for this payment group"""
        bindings = {
            'payment_group_id': self.kwargs.get('payment_group_id')}
        return self.db_handle.cursor().execute(
            self.QUERY, bindings).fetchall()


class Payment(TouchBistroDBObject):
    """This class represents a single payment on an Order.

    Required kwargs:

        - db_location: path to the database file
        - payment_uuid: the UUID for this payment
    """

    META_ATTRIBUTES = ['payment_uuid', 'payment_number', 'payment_type',
                       'payment_type_id',
                       'amount', 'tip', 'change', 'balance',
                       'refundable_amount', 'original_payment_uuid',
                       'customer_account_id', 'customer_id',
                       'card_type', 'auth_number', 'create_date']

    #: Query to get details about this discount
    QUERY = """SELECT
            ZI_TYPE,
            ZI_INDEX,
            ZACCOUNT,
            ZCUSTOMER,
            ZCARDTYPE,
            ZAUTH,
            ZI_AMOUNT,
            ZI_CHANGE,
            ZTIP,
            ZBALANCE,
            ZCREATEDATE,
            ZI_REFUNDABLEAMOUNT,
            ZORIGINALPAYMENTUUID
        FROM ZPAYMENT
        WHERE ZUUID = :payment_uuid
        """

    def __init__(self, db_location, **kwargs):
        super(Payment, self).__init__(db_location, **kwargs)
        self.payment_uuid = kwargs.get('payment_uuid')

    @property
    def payment_number(self):
        """Returns the payment number associated with this payment, by adding
        1 to ZI_INDEX to make it human readable"""
        return self.db_details['ZI_INDEX'] + 1

    @property
    def amount(self):
        """Returns the payment amount for paid orders"""
        try:
            return round(self.db_details['ZI_AMOUNT'], 2)
        except TypeError:
            return 0.0

    @property
    def tip(self):
        """Returns the tip amount for paid orders"""
        try:
            return round(self.db_details['ZTIP'], 2)
        except TypeError:
            return 0.0

    @property
    def change(self):
        """Returns the amount of change provided"""
        try:
            return round(self.db_details['ZI_CHANGE'], 2)
        except TypeError:
            return 0.0

    @property
    def refundable_amount(self):
        """Returns the refundable amount of the order"""
        try:
            return round(self.db_details['ZI_REFUNDABLEAMOUNT'], 2)
        except TypeError:
            return 0.0

    @property
    def original_payment_uuid(self):
        """If this was a refund payment, return the UUID of the original
        payment that was refunded (in a fully-integrated refund scenario)."""
        return self.db_details['ZORIGINALPAYMENTUUID']

    def is_refund(self):
        "Return true if this is a refund payment"
        raise NotImplementedError("is_refund() doesn't work yet")

    @property
    def balance(self):
        """Returns the remaining balance after the payment was made"""
        try:
            return round(self.db_details['ZBALANCE'], 2)
        except TypeError:
            return 0.0

    @property
    def payment_type_id(self):
        """Returns a payment type ID for the order (based on ZI_TYPE column)"""
        return self.db_details['ZI_TYPE']

    @property
    def payment_type(self):
        """Returns a payment type for the order (based on ZI_TYPE column)"""
        return payment_type_name(self.payment_type_id)

    @property
    def customer_account_id(self):
        """Return an ID number for a customer account associated with the
        payment, if there was one (ZACCOUNT column)"""
        return self.db_details['ZACCOUNT']

    @property
    def customer_id(self):
        """Returns the ID of a Customer associated with the payment, if
        present (ZCUSTOMER column)"""
        return self.db_details['ZCUSTOMER']

    @property
    def card_type(self):
        """When payment cards are used, return the card type"""
        return self.db_details['ZCARDTYPE']

    @property
    def auth_number(self):
        """When payment cards are used, return the card authorization #"""
        return self.db_details['ZAUTH']

    @property
    def create_date(self):
        """Returns a Python Datetime object with local timezone corresponding
        to the time that the payment occurred"""
        try:
            return cocoa_2_datetime(self.db_details['ZCREATEDATE'])
        except TypeError:
            return None

    def receipt_form(self):
        """Output payment info in a form suitable for receipts"""
        pay_type = ""
        if self.payment_type == PAYMENT_TYPES[0]:  # cash
            pay_type = "CASH"
        else:
            pay_type = self.card_type.upper()
        if self.auth_number:
            pay_type += f" [{self.auth_number}]"
        output = (
            f"Payment {self.payment_number:2d}: {pay_type:20s} "
            '      ' + f"${self.amount:3.2f}\n"
        )
        output += ' ' * 33 + f"Tip:  ${self.tip:3.2f}\n"
        output += ' ' * 19 + f"Remaining Balance:  ${self.balance:3.2f}\n"
        if self.payment_type == PAYMENT_TYPES[4]:  # customer account
            cust_acct_info = f"Account ID: {self.customer_account_id:6d}"
            output += (
                f"{cust_acct_info:>45}\n"
            )
        return output

    def _fetch_entry(self):
        """Returns the db row for this modifier"""
        bindings = {
            'payment_uuid': self.payment_uuid}
        return self.db_handle.cursor().execute(
            self.QUERY, bindings
        ).fetchone()
