"""Contain classes and functions for working with order item modifiers"""
import logging
from lib7shifts.cmd.common import Sync7Shifts2Sqlite


class ItemModifier(Sync7Shifts2Sqlite):
    """Class to represent an order item Modifier in TouchBistro. Corresponds
    to the ZMODIFIER table.

    Required kwards:

        - db_location
        - modifier_uuid: Key to the ZMODIFIER table

    Schema::

        CREATE TABLE ZMODIFIER (
            Z_PK INTEGER PRIMARY KEY,
            Z_ENT INTEGER,
            Z_OPT INTEGER,
            ZI_INDEX INTEGER,
            ZREQUIREDMODIFIER INTEGER,
            ZCONTAINERORDERITEM INTEGER,
            ZMENUITEM INTEGER,
            ZMODIFIERGROUP INTEGER,
            ZMODIFIERGROUPFORMENUITEM INTEGER,
            ZORDERITEM INTEGER,
            ZCREATEDATE TIMESTAMP,
            ZI_PRICE FLOAT,
            ZI_NAME VARCHAR,
            ZUUID VARCHAR
        );

    """

    #: Query to get details about this discount
    QUERY = """SELECT
        ZMODIFIER.*,
        ZMENUITEM.ZNAME AS MENU_ITEM_NAME
        FROM ZMODIFIER
        LEFT JOIN ZMENUITEM ON
            ZMENUITEM.Z_PK = ZMODIFIER.ZMENUITEM
        WHERE ZMODIFIER.ZUUID = :modifier_uuid
        """

    def __init__(self, db_location, **kwargs):
        super(ItemModifier, self).__init__(db_location, **kwargs)
        self.log = logging.getLogger("{}.{}".format(
            self.__class__.__module__, self.__class__.__name__
        ))
        self.modifier_uuid = kwargs.get('modifier_uuid')
        self._db_details = None

    @property
    def modifier_id(self):
        "Returns the Z_PK version of the modifier ID (UUID is better)"
        return self.db_details['Z_PK']

    @property
    def is_required(self):
        "Returns True if this was a required modifier"
        if self.db_details['ZREQUIREDMODIFIER']:
            return True
        return False

    @property
    def container_order_item_id(self):
        "Returns the ID of the OrderItem that this modifier is associated with"
        return self.db_details['ZCONTAINERORDERITEM']

    @property
    def menu_item_id(self):
        "Returns the simple Z_PK version of the menu item ID for this modifier"
        return self.db_details['ZMENUITEM']

    @property
    def modifier_group_id(self):
        "Returns the ID of the modifier group this modifier was a part of"
        return self.db_details['ZMODIFIERGROUP']

    @property
    def modifier_group_for_menu_item(self):
        """Return the ID of the modifier group associated with the menu item
        from :attr:`menu_item_id` above, in situations where the modifier came
        about as a result of a nested choice of a menu item with its own
        modifiers"""
        return self.db_details['ZMODIFIERGROUPFORMENUITEM']

    @property
    def order_item(self):
        """If a menu item was chosen as a modifer, returns the corresponding
        order item ID for that item"""
        return self.db_details['ZORDERITEM']

    @property
    def creation_date(self):
        """Returns a datetime object (in local timezone) corresponding to the
        time that the modifier was created. Does not appear to be used."""
        return self.db_details['ZCREATEDATE']

    @property
    def price(self):
        "Return the price associated with the modifier"
        return self.db_details['ZI_PRICE']

    @property
    def name(self):
        "Returns the name associated with the modifier (incl custom text)"
        if self.menu_item_id:
            return self.db_details['MENU_ITEM_NAME']
        return self.db_details['ZI_NAME']

    @property
    def db_details(self):
        "Returns cached results for the :attr:`QUERY` specified above"
        if self._db_details is None:
            self._db_details = dict()
            result = self._fetch_modifier()
            for key in result.keys():
                # perform the dict copy
                self._db_details[key] = result[key]
        return self._db_details

    def _fetch_modifier(self):
        """Returns the db row for this modifier"""
        bindings = {
            'modifier_uuid': self.modifier_uuid}
        return self.db_handle.cursor().execute(
            self.QUERY, bindings
        ).fetchone()

    def receipt_form(self):
        """Output the modifier in a form suitable for receipts and chits"""
        try:
            output = "+ "
            if self.price > 0:
                output += f"${self.price:3.2f}: "
            output += f"{self.name}\n"
            return output
        except Exception as err:
            raise RuntimeError(
                "Caught exception while processing modifier {}:\n{}".format(
                    self.modifier_uuid,
                    err
                )
            )

    def summary(self):
        """Returns a dictionary summary of this modifier"""
        summary = {'meta': dict()}
        fields = ['modifier_uuid', 'modifier_id', 'name', 'price',
                  'is_required', 'container_order_item_id', 'menu_item_id',
                  'modifier_group_id', 'modifier_group_for_menu_item',
                  'order_item', 'creation_date']
        for field in fields:
            summary['meta'][field] = getattr(self, field)
        return summary

    def __str__(self):
        "Return a pretty string to represent the waiter"
        return (
            f"Modifier(\n"
            f"  modifier_uuid: {self.modifier_uuid}\n"
            f"  modifier_id: {self.modifier_id}\n"
            f"  name: {self.name}\n"
            f"  price: {self.price}\n"
            f"  is_required: {self.is_required}\n"
            f"  container_order_item_id: {self.container_order_item_id}\n"
            f"  menu_item_id: {self.menu_item_id}\n"
            f"  modifier_group_id: {self.modifier_group_id}\n"
            "  modifier_group_for_menu_item: "
            f"{self.modifier_group_for_menu_item}\n"
            f"  order_item: {self.order_item}\n"
            f"  creation_date: {self.creation_date}\n"
            ")"
        )
