"""Contain classes and functions for reeading and reporting on Waiters"""
from .base import TouchBistroDBObject


class Waiter(TouchBistroDBObject):
    """Class to represent a Staff Member (waiter) in TouchBistro. Corresponds
    to the ZWAITER table.

    Required kwards:

        - db_location
        - waiter_uuid: Key to the ZWAITER table
    """

    META_ATTRIBUTES = ['waiter_uuid', 'waiter_id', 'display_name', 'firstname',
                       'lastname', 'email']

    #: Query to get details about this discount
    QUERY = """SELECT
        *
        FROM ZWAITER
        WHERE ZUUID = :waiter_uuid
        """

    QUERY_BINDING_ATTRIBUTES = ['waiter_uuid']

    def __init__(self, db_location, **kwargs):
        super(Waiter, self).__init__(db_location, **kwargs)
        self.waiter_uuid = kwargs.get('waiter_uuid')

    @property
    def waiter_id(self):
        "Returns the Z_PK version of the waiter ID (UUID is better)"
        return self.db_results['Z_PK']

    @property
    def staff_discount(self):
        "Returns the integer percent this staff receives as a discount"
        return self.db_results['ZDISCOUNTPERCENT']

    @property
    def display_name(self):
        "Returns the display name for this waiter"
        return self.db_results['ZDISPLAYNAME']

    @property
    def email(self):
        "Returns the email address set up for this waiter"
        return self.db_results['ZEMAIL']

    @property
    def firstname(self):
        "Returns the firstname set for this waiter"
        return self.db_results['ZFIRSTNAME']

    @property
    def lastname(self):
        "Returns the lastname set for this waiter"
        return self.db_results['ZLASTNAME']

    @property
    def fullname(self):
        "Returns a simple concatenation of firstname and lastname"
        return f"{self.firstname} {self.lastname}"

    @property
    def passcode(self):
        "Returns the passcode the user uses to log into TouchBistro"
        return self.db_results['ZPASSCODE']
