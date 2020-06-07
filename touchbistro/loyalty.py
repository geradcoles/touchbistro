"""The Loyalty module covers classes and methods related to spending and
charging up of TouchBistro Loyalty cards/accounts."""
from .base import TouchBistroDBObject
from .waiter import Waiter
from .dates import cocoa_2_datetime

LOYALTY_ACTIVITY_TYPE_MAP = {
    0: "Reduce Balance",
    4: "Add Balance"
}

LOYALTY_TYPE_MAP = {
    0: "Loyalty Account"
}


class LoyaltyActivity(TouchBistroDBObject):
    """This class represents activity on a TouchBistro Loyalty Card
    or account, such as loading balance or spending it. Balances can be
    loaded in TouchBistro without any sales/payments, and they can be loaded
    outside of TouchBistro directly from the Loyalty website, so the code in
    this module is half-blind as to what's going on.

    Mainly, this class is used to add information to loyalty-related payments,
    such as the full ID of the loyalty card, with is found in the ZUSERNAME
    column of the ZLOYALTYACTIVITYLOG table represented by this class.

    Required kwargs:

    - transaction_id: corresponds to auth # for loyalty
                   payment transactions.
    """

    QUERY = """SELECT
        *
    FROM ZLOYALTYACTIVITYLOG
    WHERE
        ZTRANSACTIONID = :transaction_id
    LIMIT 1"""

    QUERY_BINDING_ATTRIBUTES = ['transaction_id']

    META_ATTRIBUTES = [
        'transaction_id', 'datetime', 'activity_type_id', 'account_type',
        'activity_type_name', 'amount', 'account_type', 'waiter_name',
        'user_id', 'account_number']

    @property
    def activity_type_id(self):
        """Returns an integer corresponding to the type of activity to the
        loyalty account. See LOYALTY_ACTIVITY_TYPE_MAP for details"""
        return self.db_results['ZACTIVITYTYPE']

    @property
    def activity_type_name(self):
        """Returns a text representation of the type of activitiy applied to
        the loyalty card, from :attr:`LOYALTY_ACTIVITY_TYPE_MAP` above."""
        return LOYALTY_ACTIVITY_TYPE_MAP[self.activity_type_id]

    @property
    def account_type(self):
        """Returns a loyalty account type based on LOYALTY_TYPE_MAP above"""
        try:
            return LOYALTY_TYPE_MAP[self.db_results['ZLOYALTYTYPE']]
        except KeyError:
            return "Unknown"

    @property
    def amount(self):
        """Return the amount of the change (unsigned)"""
        return self.db_results['ZAMOUNT']

    @property
    def balance_change(self):
        """Same as :attr:`amount`, but signed correctly for balance in
        (positive), or balance out (negative)"""
        if self.activity_type_id == 0:
            return - self.amount
        return self.amount

    @property
    def datetime(self):
        """Return a datetime object for the date and time that the change was
        made"""
        return cocoa_2_datetime(self.db_results['ZCREATEDAT'])

    @property
    def transaction_id(self):
        """Return the transaction ID from the Loyalty interface (which matches
        the ID found as auth# for loyalty card payments)"""
        return self.db_results['ZTRANSACTIONID']

    @property
    def user_id(self):
        """Returns the ID of the loyalty user from the Loyalty interface"""
        return self.db_results['ZUSERID']

    @property
    def account_number(self):
        """Returns the loyalty account number associated with the transaction.
        (This is from the ZUSERNAME column)"""
        return self.db_results['ZUSERNAME']

    @property
    def waiter_uuid(self):
        """Returns the UUID for the waiter that made the change to the loyalty
        account"""
        return self.db_results['ZWAITERUUID']

    @property
    def waiter(self):
        """Return a :class:`Waiter` object corresponding to the person who made
        the change to the loyalty account"""
        return Waiter(
            self._db_location,
            waiter_uuid=self.waiter_uuid,
            parent=self
        )

    @property
    def waiter_name(self):
        """Look up and return the waiter display name for the person who made
        the change to the loyalty account"""
        return self.waiter.display_name
