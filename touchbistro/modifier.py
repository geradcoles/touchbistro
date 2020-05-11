"""Contain classes and functions for working with order item modifiers"""
from .base import TouchBistroDBObject, TouchBistroObjectList


class ItemModifierList(TouchBistroObjectList):
    """Use this class to get a list of ItemModifier objects for an OrderItem.
    It behaves like a sequence, where you can simply iterate over the object,
    or call it with an index to get a particular item.

    kwargs:
        - order_item_id
    """

    #: Query to get a list of modifier uuids for this order item
    QUERY = """SELECT
        ZUUID
        FROM ZMODIFIER
        WHERE ZCONTAINERORDERITEM = :order_item_id
        ORDER BY ZI_INDEX ASC
        """

    def total(self):
        "Returns the total value of modifiers in the list"
        amount = 0.0
        for modifier in self.items:
            amount += modifier.price
        return amount

    @property
    def items(self):
        "Returns the discounts as a list, caching db results"
        if self._items is None:
            self._items = list()
            for row in self._fetch_items():
                self._items.append(
                    ItemModifier(
                        self._db_location,
                        modifier_uuid=row['ZUUID']))
        return self._items

    def _fetch_items(self):
        """Returns a list of modifier uuids from the DB for this order
        item"""
        bindings = {
            'order_item_id': self.kwargs.get('order_item_id')}
        return self.db_handle.cursor().execute(
            self.QUERY, bindings
        ).fetchall()


class ItemModifier(TouchBistroDBObject):
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

    META_ATTRIBUTES = ['modifier_uuid', 'modifier_id', 'name', 'price',
                       'is_required', 'container_order_item_id',
                       'menu_item_id',
                       'modifier_group_id', 'modifier_group_for_menu_item',
                       'order_item', 'creation_date']

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
        self.modifier_uuid = kwargs.get('modifier_uuid')

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

    def _fetch_entry(self):
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
