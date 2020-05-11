"""Contain classes and functions for reeading and reporting on Waiters"""
from .base import TouchBistroDB


class Waiter(TouchBistroDB):
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

    def __init__(self, db_location, **kwargs):
        super(Waiter, self).__init__(db_location, **kwargs)
        self.waiter_uuid = kwargs.get('waiter_uuid')

    @property
    def waiter_id(self):
        "Returns the Z_PK version of the waiter ID (UUID is better)"
        return self.db_details['Z_PK']

    @property
    def staff_discount(self):
        "Returns the integer percent this staff receives as a discount"
        return self.db_details['ZDISCOUNTPERCENT']

    @property
    def display_name(self):
        "Returns the display name for this waiter"
        return self.db_details['ZDISPLAYNAME']

    @property
    def email(self):
        "Returns the email address set up for this waiter"
        return self.db_details['ZEMAIL']

    @property
    def firstname(self):
        "Returns the firstname set for this waiter"
        return self.db_details['ZFIRSTNAME']

    @property
    def lastname(self):
        "Returns the lastname set for this waiter"
        return self.db_details['ZLASTNAME']

    @property
    def fullname(self):
        "Returns a simple concatenation of firstname and lastname"
        return f"{self.firstname} {self.lastname}"

    @property
    def passcode(self):
        "Returns the passcode the user uses to log into TouchBistro"
        return self.db_details['ZPASSCODE']

    def _fetch_entry(self):
        """Returns the db row for this waiter"""
        bindings = {
            'waiter_uuid': self.waiter_uuid}
        return self.db_handle.cursor().execute(
            self.QUERY, bindings
        ).fetchone()
