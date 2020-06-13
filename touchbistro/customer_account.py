"""This module represents TouchBistro Customer Accounts, which can be loaded
up with balance through pay-in type operations, and used to pay for customer
orders. Customer accounts can go negative in balance.
"""
from .base import TouchBistroDBObject


class CustomerAccountActivity(TouchBistroDBObject):
    """This class represents activity on a TouchBistro Customer Account,
    including paying into the account, or spending from it. Generally, this
    class will be instantiated by :class:`touchbistro.payment.Payment`, as it
    finds orders paid with a customer account.

    Pass in this required kwarg:

    - transaction_id: corresponds to the customer account ID used for the
                    transaction
    """


class CustomerAccount(TouchBistroDBObject):
    """This class represents a Customer Account and includes information about
    the account, such as the customer name and current balance. Based on the
    ZTBACCOUNT table. Note that many columns in this table appear to be unused,
    and are left out of class attributes because we haven't seen a benefit to
    including them.

    Pass in the following kwargs:

    - customer_account_id: the Z_PK account id for the ZTBACCOUNT table
    """
    #: The ZTBACCOUNT table has a column with incremental versioning in the
    #: name. Use this to keep track of determined version numbers centrally.
    __VERSION = 77

    QUERY = """SELECT
        *
    FROM ZTBACCOUNT
    WHERE Z_PK = :customer_account_id
    """
    QUERY_BINDING_ATTRIBUTES = ['customer_account_id']

    META_ATTRIBUTES = []

    @property
    def favourite(self):
        """Returns an integer for "favourite" accounts. (behaviour unknown)"""
        return self.db_results['ZFAVOURITE']

    @property
    def accounts(self):
        """Returns a foreign key to an accounts table. Based on a column name
        that continues to increment with releases"""
        for _ in range(100):
            colname = 'Z' + str(CustomerAccount.__VERSION) + 'ACCOUNTS'
            try:
                return self.db_results[colname]
            except KeyError:
                pass
            CustomerAccount.__VERSION += 1
        raise RuntimeError("Can't find a suitable ZXXACCOUNTS column")

    @property
    def balance(self):
        """Returns the current floating-point balance on the account. Negative
        balances indicate amounts owing to the customer (a debt to the
        customer)."""
        return self.db_results['ZBALANCE']

    @property
    def email(self):
        """Returns the customer email, if set"""
        return self.db_results['ZEMAIL']

    @property
    def name(self):
        """Returns the customer name"""
        return self.db_results['ZNAME']

    @property
    def note(self):
        """Returns any note attached to the customer account"""
        return self.db_results['ZNOTE']

    @property
    def customer_number(self):
        """Returns the ZNUMBER field, a customer number, if set"""
        return self.db_results['ZNUMBER']

    @property
    def phone_number(self):
        """Returns the customer phone number, if set"""
        return self.db_results['ZPHONENUMBER']
