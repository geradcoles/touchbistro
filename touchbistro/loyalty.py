"""The Loyalty module covers classes and methods related to spending and
charging up of TouchBistro Loyalty cards/accounts."""
from datetime import timedelta
from .base import TouchBistroDBObject, TouchBistroObjectList
from .waiter import Waiter
from .dates import cocoa_2_datetime, datetime_2_cocoa, to_local_datetime

LOYALTY_ACTIVITY_TYPE_MAP = {
    0: "Reduce Balance",
    4: "Add Balance"
}

LOYALTY_TYPE_MAP = {
    0: "Loyalty Account"
}


def get_loyalty_for_date_range(
        db_location, earliest_date, latest_date, day_boundary='02:00:00'):
    """Given an earliest and a latest date, return an LoyaltyActivityByDate
    object containing all the orders for that date period. latest_date is
    inclusive, so if you specify 2020-05-31 as the latest_date, all orders from
    that day will be included in the results.

    Dates should be in the YYYY-MM-DD format. The local timezone will be used
    by default. Use the day_boundary parameter to set a reasonable time to
    transition from one day to the next, if your restaurant has cash
    transactions after midnight (default is 02:00:00).
    """
    return LoyaltyActivityByDate(
        db_location,
        earliest_time=to_local_datetime(earliest_date + ' ' + day_boundary),
        cutoff_time=to_local_datetime(
            latest_date + ' ' + day_boundary) + timedelta(days=1)
    )


class LoyaltyActivityByDate(TouchBistroObjectList):
    """Use this class to get a list of LoyaltyActivity objects for the given
    date range.

    kwargs:
        - earliest_time (datetime object)
        - cutoff_time (datetime object)
    """

    #: Query to get a list of modifier uuids for this order item
    QUERY = """SELECT
        ZTRANSACTIONID
    FROM ZLOYALTYACTIVITYLOG
    WHERE
        ZCREATEDAT >= :earliest_time AND
        ZCREATEDAT < :cutoff_time
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
        return LoyaltyActivity(
            self._db_location,
            transaction_id=row['ZTRANSACTIONID'],
            parent=self.parent)


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
