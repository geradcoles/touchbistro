"""Contain classes and functions for working with order item modifiers"""
from .base import TouchBistroDBObject, TouchBistroObjectList
from .menu import MenuItem


def modifier_sales_category_amounts(modifier, output=None):
    """Look at a modifier and collect its Sales Category
    and Price, and check those to see if they have further nested
    modifiers, cataloging the values and sales categories into
    a dictionary, where the keys are SalesCategory objects and the
    values are the total price of the modifiers for that category.
    Supports/uses recursion. You can provide an output dict from
    a parent object or leave output empty to start from this level"""
    if output is None:
        output = dict()
    if modifier.sales_category in output:
        output[modifier.sales_category] += modifier.price
    else:
        output[modifier.sales_category] = modifier.price
    for submod in modifier.nested_modifiers:
        modifier_sales_category_amounts(submod, output)
    return output


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

    QUERY_BINDING_ATTRIBUTES = ['order_item_id']

    def total(self):
        "Returns the total value of modifiers in the list"
        amount = 0.0
        for modifier in self.items:
            amount += modifier.price
            amount += modifier.nested_modifiers.total()
        return amount

    def _vivify_db_row(self, row):
        "Convert a db row to an ItemModifier"
        return ItemModifier(
            self._db_location, modifier_uuid=row['ZUUID'],
            parent=self.parent)

    @property
    def tax1_taxable_subtotal(self):
        "Returns the tax 1 taxable subtotal for all items (incl. nested)"
        subtotal = 0.0
        for item in self.items:
            subtotal += item.tax1_taxable_subtotal
        return subtotal

    @property
    def tax2_taxable_subtotal(self):
        "Returns the tax 2 taxable subtotal for all items (incl. nested)"
        subtotal = 0.0
        for item in self.items:
            subtotal += item.tax2_taxable_subtotal
        return subtotal

    @property
    def tax3_taxable_subtotal(self):
        "Returns the tax 3 taxable subtotal for all items (incl. nested)"
        subtotal = 0.0
        for item in self.items:
            subtotal += item.tax3_taxable_subtotal
        return subtotal


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

    META_ATTRIBUTES = ['name', 'price',
                       'is_required', 'container_order_item_id',
                       'menu_item_id', 'sales_category',
                       'modifier_group_id', 'modifier_group_for_menu_item',
                       'order_item', 'datetime', 'waiter_name']

    #: Query to get details about this modifier
    QUERY = """SELECT
        ZMODIFIER.*,
        ZMENUITEM.ZNAME AS MENU_ITEM_NAME,
        ZMENUITEM.ZUUID AS MENU_ITEM_UUID
        FROM ZMODIFIER
        LEFT JOIN ZMENUITEM ON
            ZMENUITEM.Z_PK = ZMODIFIER.ZMENUITEM
        WHERE ZMODIFIER.ZUUID = :modifier_uuid
        """

    QUERY_BINDING_ATTRIBUTES = ['modifier_uuid']

    @property
    def object_type(self):
        "Returns the name of this object's class"
        if self.kwargs.get('is_nested', None):
            return 'Nested' + self.__class__.__name__
        return self.__class__.__name__

    @property
    def is_required(self):
        "Returns True if this was a required modifier"
        if self.db_results['ZREQUIREDMODIFIER']:
            return True
        return False

    @property
    def container_order_item_id(self):
        "Returns the ID of the OrderItem that this modifier is associated with"
        return self.db_results['ZCONTAINERORDERITEM']

    @property
    def menu_item_id(self):
        "Returns the simple Z_PK version of the menu item ID for this modifier"
        return self.db_results['ZMENUITEM']

    @property
    def menu_item_uuid(self):
        "Returns the UUID of an associate menu item, if applicable"
        return self.db_results['MENU_ITEM_UUID']

    @property
    def waiter_name(self):
        """Tries to return a waiter name for this modifier, using the parent
        item's waiter name"""
        return self.parent.waiter_name

    @property
    def menu_item(self):
        """Return a MenuItem object representing the associated menu item, or
        None"""
        if self.menu_item_uuid:
            return MenuItem(
                db_location=self._db_location,
                menuitem_uuid=self.menu_item_uuid,
                parent=self)
        return None

    @property
    def sales_category(self):
        """If this is a menu-based modifier, returns the sales category name
        for the menu item tied to the modifier. If not a menu-based modifier,
        tries to return the sales category name from the parent, if provided,
        otherwise 'None'"""
        if self.menu_item_uuid:
            return self.menu_item.sales_category.name
        try:
            return self.parent.sales_category
        except AttributeError:
            return None

    @property
    def modifier_group_id(self):
        "Returns the ID of the modifier group this modifier was a part of"
        return self.db_results['ZMODIFIERGROUP']

    @property
    def modifier_group_for_menu_item(self):
        """Return the ID of the modifier group associated with the menu item
        from :attr:`menu_item_id` above, in situations where the modifier came
        about as a result of a nested choice of a menu item with its own
        modifiers"""
        return self.db_results['ZMODIFIERGROUPFORMENUITEM']

    @property
    def order_item(self):
        """For nested modifers, return the corresponding order item ID that
        may/should have further modifiers associated with it."""
        return self.db_results['ZORDERITEM']

    @property
    def nested_modifiers(self):
        """Returns an ItemModifierList containing any nested modifiers"""
        return ItemModifierList(
            self._db_location,
            order_item_id=self.order_item,
            parent=self.parent,
            is_nested=True)

    @property
    def datetime(self):
        """Returns a datetime object (in local timezone) corresponding to the
        time that the modifier was created. Does not appear to be used."""
        if self.db_results['ZCREATEDATE']:
            return self.db_results['ZCREATEDATE']
        try:
            return self.parent.datetime
        except AttributeError:
            return None

    @property
    def price(self):
        "Return the price associated with the modifier, adjusted for quantity"
        return self.parent.quantity * self.db_results['ZI_PRICE']

    @property
    def tax1_taxable_subtotal(self):
        """Crawl through modifier and nested sub-entities and return a the
        tax1 subtotal for all menu-based entities that have tax settings.
        For non-menu-based modifiers, always returns the full price of the
        modifier, including any nested entities."""
        subtotal = 0.0
        if self.is_menu_based() and self.menu_item.exclude_tax1:
            pass
        else:
            subtotal += self.price
        for modifier in self.nested_modifiers:
            subtotal += modifier.tax1_taxable_subtotal
        return subtotal

    @property
    def tax2_taxable_subtotal(self):
        """Crawl through modifier and nested sub-entities and return a the
        tax2 subtotal for all menu-based entities that have tax settings.
        For non-menu-based modifiers, always returns the full price of the
        modifier, including any nested entities."""
        subtotal = 0.0
        if self.is_menu_based() and self.menu_item.exclude_tax2:
            pass
        else:
            subtotal += self.price
        for modifier in self.nested_modifiers:
            subtotal += modifier.tax2_taxable_subtotal
        return subtotal

    @property
    def tax3_taxable_subtotal(self):
        """Crawl through modifier and nested sub-entities and return a the
        tax3 subtotal for all menu-based entities that have tax settings.
        For non-menu-based modifiers, always returns the full price of the
        modifier, including any nested entities."""
        subtotal = 0.0
        if self.is_menu_based() and self.menu_item.exclude_tax3:
            pass
        else:
            subtotal += self.price
        for modifier in self.nested_modifiers:
            subtotal += modifier.tax3_taxable_subtotal
        return subtotal

    @property
    def name(self):
        "Returns the name associated with the modifier (incl custom text)"
        if self.menu_item_id:
            return self.db_results['MENU_ITEM_NAME']
        return self.db_results['ZI_NAME']

    def is_menu_based(self):
        "Return True if this is a menu-based modifier"
        if self.menu_item:
            return True
        return False

    def receipt_form(self, depth=1):
        """Output the modifier in a form suitable for receipts and chits"""
        try:
            output = "  " * depth
            output += "+ "
            if self.price > 0:
                output += f"${self.price:3.2f}: "
            output += f"{self.name}\n"
            for modifier in self.nested_modifiers:
                output += modifier.receipt_form(depth=(depth+1))
            return output
        except Exception as err:
            raise RuntimeError(
                "Caught exception while processing modifier {}:\n{}".format(
                    self.uuid,
                    err
                )
            )
