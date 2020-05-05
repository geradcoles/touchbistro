"""Contain classes and functions for reeading and reporting on Waiters"""
import logging
from lib7shifts.cmd.common import Sync7Shifts2Sqlite


class Waiter(Sync7Shifts2Sqlite):
    """Class to represent a Staff Member (waiter) in TouchBistro. Corresponds
    to the ZWAITER table.

    Required kwards:

        - db_location
        - waiter_uuid: Key to the ZWAITER table
    """

    #: Query to get details about this discount
    QUERY = """SELECT
        *
        FROM ZWAITER
        WHERE ZUUID = :waiter_uuid
        """

    def __init__(self, db_location, **kwargs):
        super(Waiter, self).__init__(db_location, **kwargs)
        self.log = logging.getLogger("{}.{}".format(
            self.__class__.__module__, self.__class__.__name__
        ))
        self.waiter_uuid = kwargs.get('waiter_uuid')
        self._db_details = None

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

    @property
    def db_details(self):
        "Returns cached results for the :attr:`QUERY` specified above"
        if self._db_details is None:
            self._db_details = dict()
            result = self._fetch_waiter()
            for key in result.keys():
                # perform the dict copy
                self._db_details[key] = result[key]
        return self._db_details

    def _fetch_waiter(self):
        """Returns the db row for this waiter"""
        bindings = {
            'waiter_uuid': self.waiter_uuid}
        return self.db_handle.cursor().execute(
            self.QUERY, bindings
        ).fetchone()

    def summary(self):
        """Returns a dictionary of attributes about this waiter"""
        summary = {'meta': dict()}
        fields = ['waiter_uuid', 'waiter_id', 'display_name', 'firstname',
                  'lastname', 'email']
        for field in fields:
            summary['meta'][field] = getattr(self, field)
        return summary

    def __str__(self):
        "Return a pretty string to represent the waiter"
        return (
            f"Waiter(\n"
            f"  waiter_uuid: {self.waiter_uuid}\n"
            f"  waiter_id: {self.waiter_id}\n"
            f"  display_name: {self.display_name}\n"
            f"  firstname: {self.firstname}\n"
            f"  lastname: {self.lastname}\n"
            f"  email: {self.email}\n"
            ")"
        )
