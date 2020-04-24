"""Module to handle queries on the ZPAIDORDER table
"""
import logging
from lib7shifts.dates import _get_epoch_ts_for_date
from lib7shifts.cmd.common import Sync7Shifts2Sqlite

class PaidOrderSummary(Sync7Shifts2Sqlite):
    """Obtain a paid order summary for the given date range.

    kwargs:

    - earliest (float): epoch timestamp for start of date range
    - cutoff (float): epoch timestamp for end of date range (exclusive)

    Results are a two-column format containing EpochDate and Amount.
    """

    QUERY_PAID_ORDER_SUMMARY = """SELECT
            (ZPAIDORDER.ZPAYDATE + 978307200) as EpochDate,
            ifnull(round(ZPAYMENT.ZI_AMOUNT + 0.0, 2), 0.0) as Amount
        FROM ZPAIDORDER
        LEFT JOIN ZPAYMENT ON ZPAYMENT.ZPAYMENTGROUP = ZPAIDORDER.ZPAYMENTS
        WHERE
            ZPAIDORDER.ZPAYDATE >= :earliest AND
            ZPAIDORDER.ZPAYDATE < :cutoff
    """

    def __init__(self, db_location, **kwargs):
        super(PaidOrderSummary, self).__init__(db_location, **kwargs)
        self.log = logging.getLogger("{}.{}".format(
            self.__class__.__module__, self.__class__.__name__
        ))
        self.earliest = kwargs.get('earliest')
        self.cutoff = kwargs.get('cutoff')
    
    def summary(self):
        """Returns a summary list of dicts as per the class summary"""
        bindings = {'earliest': self.earliest, 'cutoff': self.cutoff}
        return self.db_handle.cursor().execute(
            self.QUERY_PAID_ORDER_SUMMARY, bindings
        )
