"""Module to handle queries on the ZPAIDORDER table
"""
import logging
from lib7shifts.dates import _get_epoch_ts_for_date
from lib7shifts.cmd.common import Sync7Shifts2Sqlite
from .dates import unixepoch_2_cocoa


def takeout_type_pretty(value):
    "Returns a friendly takeout type from a mapped value"
    return ZI_TAKEOUTTYPE_MAP[value]


ZI_TAKEOUTTYPE_MAP = {
    None: 'dinein',
    0: 'takeout',
    1: 'delivery',
    2: 'bartab'
}


class PaidOrders(Sync7Shifts2Sqlite):
    """Obtain a paid order summary for the given date range.

    kwargs:

    - earliest (float): epoch timestamp for start of date range
    - cutoff (float): epoch timestamp for end of date range (exclusive)

    Results are a multi-column format containing details about each payment.
    Orders with multiple payments will have a row per payment.
    """

    QUERY_PAID_ORDER_SUMMARY = """SELECT
            (ZPAIDORDER.ZPAYDATE + 978307200) as Timestamp,
            ZPAIDORDER.ZI_BILLNUMBER as Bill,
            ZPAIDORDER.ZI_TAKEOUTTYPE as Order_Type,
            ZPAYMENT.ZCARDTYPE as Payment_Type,
            ifnull(round(ZPAYMENT.ZI_AMOUNT, 2), 0.0) as Payments,
            ifnull(round(ZPAYMENT.ZTIP, 2), 0.0) as Total_Tips
        FROM ZPAIDORDER
        LEFT JOIN ZPAYMENT ON ZPAYMENT.ZPAYMENTGROUP = ZPAIDORDER.ZPAYMENTS
        WHERE
            ZPAIDORDER.ZPAYDATE >= :earliest AND
            ZPAIDORDER.ZPAYDATE < :cutoff
    """

    def __init__(self, db_location, **kwargs):
        super(PaidOrders, self).__init__(db_location, **kwargs)
        self.log = logging.getLogger("{}.{}".format(
            self.__class__.__module__, self.__class__.__name__
        ))
        self.earliest = kwargs.get('earliest')
        self.cutoff = kwargs.get('cutoff')

    def get_results(self):
        """Returns a summary list of dicts as per the class summary"""
        bindings = {
            'earliest': unixepoch_2_cocoa(self.earliest),
            'cutoff': unixepoch_2_cocoa(self.cutoff)}
        return self.db_handle.cursor().execute(
            self.QUERY_PAID_ORDER_SUMMARY, bindings
        )
