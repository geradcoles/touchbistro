"""This module contains classes and functions to work with TouchBistro
payments.
"""
import logging
from lib7shifts.cmd.common import Sync7Shifts2Sqlite
from .dates import cocoa_2_datetime


#: This map is used to generate a human-readable name for ZI_TYPE in the
#: ZPAYMENT table.
PAYMENT_TYPES = ("Cash", "Electronic", "Unknown", "Unknown", "Unknown",
                 "Customer Account")


def payment_type_name(type_id):
    "Given a payment type id, return a payment type name from PAYMENT_TYPES"
    return PAYMENT_TYPES[type_id]


class Payment(Sync7Shifts2Sqlite):
    """This class represents a single payment on an Order.

    Required kwargs:

        - db_location: path to the database file
        - payment_uuid: the UUID for this payment
    """

    META_FIELDS = ['payment_uuid', 'payment_number', 'payment_type',
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
        self.log = logging.getLogger("{}.{}".format(
            self.__class__.__module__, self.__class__.__name__
        ))
        self.payment_uuid = kwargs.get('payment_uuid')
        self._db_details = None

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

    @property
    def db_details(self):
        "Returns cached results for the :attr:`QUERY` specified above"
        if self._db_details is None:
            self._db_details = dict()
            result = self._fetch_payment()
            for key in result.keys():
                # perform the dict copy
                self._db_details[key] = result[key]
        return self._db_details

    def summary(self):
        """Return a dictionary summary of the order"""
        summary = {'meta': dict()}
        for field in self._meta_fields():
            summary['meta'][field[0]] = field[1]
        return summary

    def receipt_form(self):
        """Output payment info in a form suitable for receipts"""
        auth = ""
        if self.auth_number:
            auth = f"[{self.auth_number}]"
        pay_type = ""
        if self.payment_type == PAYMENT_TYPES[0]:  # cash
            pay_type = "CASH"
        else:
            pay_type = self.card_type.upper()
        output = (
            f"Payment {self.payment_number:2d}: {pay_type:12s} "
            f"{auth:8s}" + (' ' * 6) + f"${self.amount:3.2f}\n"
        )
        output += ' ' * 33 + f"Tip:  ${self.tip:3.2f}\n"
        output += ' ' * 19 + f"Remaining Balance:  ${self.balance:3.2f}\n"
        if self.payment_type == PAYMENT_TYPES[4]:  # customer account
            cust_acct_info = f"Account ID: {self.customer_account_id:6d}"
            output += (
                f"{cust_acct_info:>45}\n"
            )
        return output

    def _fetch_payment(self):
        """Returns the db row for this modifier"""
        bindings = {
            'payment_uuid': self.payment_uuid}
        return self.db_handle.cursor().execute(
            self.QUERY, bindings
        ).fetchone()

    def _meta_fields(self):
        """Yields an iterable of key-value pairs in 2-tuples"""
        for field in self.META_FIELDS:
            yield tuple((field, getattr(self, field)))

    def __str__(self):
        "Return a pretty-printed string-version of the payment"
        payment = "Payment(\n"
        for field in self._meta_fields():
            payment += f"  {field[0]}: {field[1]}\n"
        payment += ")\n"
