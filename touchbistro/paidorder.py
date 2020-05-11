"""Module to handle queries on the ZPAIDORDER table
"""
import logging
from .base import TouchBistroDBObject
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


class PaidOrders(TouchBistroDBObject):
    """Obtain a paid order summary for the given date range.

    kwargs:

    - earliest (float): epoch timestamp for start of date range
    - cutoff (float): epoch timestamp for end of date range (exclusive)

    Results are a multi-column format containing details about each payment.
    Orders with multiple payments will have a row per payment.
    """

    QUERY_PAID_ORDER_SUMMARY = """SELECT
            (ZPAIDORDER.ZPAYDATE + 978307200) as Timestamp,
            ZPAIDORDER.*,
            CASE ZPAIDORDER.ZI_TAKEOUTTYPE
                WHEN 2
                    THEN 'bartab'
                WHEN 1
                    THEN 'delivery'
                WHEN 0
                    THEN 'takeout'
                ELSE 'dinein'
            END ORDER_TYPE,
            ZPAYMENT.ZCARDTYPE,
            ZCUSTOMTAKEOUTTYPE.ZNAME as CUSTOMTAKEOUTTYPE,
            ifnull(round(ZPAYMENT.ZI_AMOUNT, 2), 0.0) as ZI_AMOUNT,
            ifnull(round(ZPAYMENT.ZTIP, 2), 0.0) as ZTIP
        FROM ZPAIDORDER
        LEFT JOIN ZPAYMENT ON
            ZPAYMENT.ZPAYMENTGROUP = ZPAIDORDER.ZPAYMENTS
        LEFT JOIN ZCLOSEDTAKEOUT ON
            ZCLOSEDTAKEOUT.Z_PK = ZPAIDORDER.ZCLOSEDTAKEOUT
        LEFT JOIN ZCUSTOMTAKEOUTTYPE ON
            ZCUSTOMTAKEOUTTYPE.Z_PK = ZCLOSEDTAKEOUT.ZCUSTOMTAKEOUTTYPE
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
