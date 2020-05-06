"""This module provides classes and methods for viewing and reporting on menu
items in TouchBistro"""
import logging
from lib7shifts.cmd.common import Sync7Shifts2Sqlite
from .dates import cocoa_2_datetime, datetime_2_cocoa
from .changelog import ChangeLogEntry, SearchChangeLog
from .salescategory import SalesCategory


class MenuChangeLogEntry(ChangeLogEntry):
    """This class overrides changelog.ChangeLogEntry to provide helpers for
    obtaining more details about menu changes, such as Waiter and menu item
    info.

    kwargs:

        - changelog_uuid: a uuid for the changelog entry
    """

    #: These attributes will be part of the dictionary representation
    #: of this object, as well as the string version.
    META_ATTRIBUTES = ['changelog_uuid', 'change_id', 'timestamp',
                       'change_type', 'change_type_details',
                       'object_reference',
                       'object_reference_type', 'user_uuid',
                       'value_changed_from', 'value_changed_to']

    def __init__(self, db_location, **kwargs):
        super(MenuChangeLogEntry, self).__init__(db_location, **kwargs)

    def get_menu_item(self):
        """Returns a Menu object representing the menu item being updated.
        Note that for menu items being created, the changelog table contains
        no object reference, so this method will simply return None for those
        items"""
        if self.object_reference_type == 'MenuItemUUID':
            if self.object_reference:
                return MenuItem(
                    self._db_location, menuitem_uuid=self.object_reference)
        return None


class MenuItem(Sync7Shifts2Sqlite):
    """This class represents a menu item from the ZMENUITEM table.

    kwargs:

        - menuitem_uuid: a uuid for the menuitem
    """

    #: These attributes will be part of the dictionary representation
    #: of this object, as well as the string version.
    META_ATTRIBUTES = ['menuitem_uuid', 'menu_id', 'course', 'hidden', 'index',
                       'in_stock', 'is_archived', 'is_returnable',
                       'print_seperate_chit', 'require_manager',
                       'show_in_public_menu',
                       'use_recipe_cost', 'exclude_tax1', 'exclude_tax2',
                       'exclude_tax3', 'use_recipe_cost',
                       'used_for_gift_cards', 'sales_category_type_id',
                       'menu_category_uuid', 'menu_category_id',
                       'actual_cost',
                       'approx_cooking_time', 'created_date', 'count',
                       'warn_count', 'price', 'version',
                       'full_image', 'thumb_image',
                       'description', 'parent_uuid', 'name', 'recipe',
                       'short_name', 'upc']

    #: Query to get details about this discount
    QUERY = """SELECT
            *
        FROM ZMENUITEM
        WHERE ZUUID = :menuitem_uuid
        """

    def __init__(self, db_location, **kwargs):
        super(MenuItem, self).__init__(db_location, **kwargs)
        self.log = logging.getLogger("{}.{}".format(
            self.__class__.__module__, self.__class__.__name__
        ))
        self.menuitem_uuid = kwargs.get('menuitem_uuid')
        self._menu_category = None
        self._sales_category = None
        self._db_details = kwargs.get('db_details', None)

    @property
    def menu_id(self):
        "Returns the Z_PK primary key for the menu item"
        return self.db_details['Z_PK']

    @property
    def course(self):
        "Returns the integer course number for the menu item (if set)"
        return self.db_details['ZI_COURSE']

    @property
    def exclude_tax1(self):
        "Returns True if the menu item is excluded from Tax 1"
        return self.db_details['ZI_EXCLUDETAX1']

    @property
    def exclude_tax2(self):
        "Returns True if the menu item is excluded from Tax 2"
        return self.db_details['ZI_EXCLUDETAX2']

    @property
    def exclude_tax3(self):
        "Returns True if the menu item is excluded from Tax 3"
        return self.db_details['ZI_EXCLUDETAX3']

    @property
    def hidden(self):
        "Returns True if the menu item should be hidden"
        return self.db_details['ZI_HIDDEN']

    @property
    def index(self):
        "Returns the index number for the menu item (in a menu category)"
        return self.db_details['ZI_INDEX']

    @property
    def in_stock(self):
        "Returns True if the menu item is in stock"
        return self.db_details['ZINSTOCK']

    @property
    def is_archived(self):
        "Returns True if the menu item is archived (deleted)"
        return self.db_details['ZISARCHIVED']

    @property
    def is_returnable(self):
        "Returns True if the menu item is returnable"
        return self.db_details['ZISRETURNABLE']

    @property
    def print_seperate_chit(self):
        "Returns True if the menu item should be printed on its own chit"
        return self.db_details['ZPRINTSEPERATECHIT']

    @property
    def require_manager(self):
        "Returns True if the menu item requires a manager to order"
        return self.db_details['ZREQUIREMANAGER']

    @property
    def show_in_public_menu(self):
        "Returns True if the menu item should be shown in the public menu"
        return self.db_details['ZSHOWINPUBLICMENU']

    @property
    def sales_category_type_id(self):
        "Returns the sales category type as an integer ID"
        return self.db_details['ZTYPE']

    @property
    def sales_category(self):
        "Returns a sales category object for the menu item"
        if self._sales_category is None:
            self._sales_category = SalesCategory(
                self._db_location,
                category_type_id=self.sales_category_type_id)
        return self._sales_category

    @property
    def use_recipe_cost(self):
        "Returns True if the menu item should be costed based on a recipe"
        return self.db_details['ZUSERECIPECOST']

    @property
    def used_for_gift_cards(self):
        "Returns True if the menu item is used to purchase gift cards"
        return self.db_details['ZUSEDFORGIFTCARDS']

    @property
    def menu_category_id(self):
        "Returns the menu category id associated with this menu item"
        return self.db_details['ZCATEGORY']

    @property
    def menu_category_uuid(self):
        "Returns the menu category uuid associated with this menu item"
        return self.db_details['ZCATEGORYUUID']

    @property
    def menu_category(self):
        "Returns a MenuCategory object corresponding to the menu item"
        if self._menu_category is None:
            self._menu_category = MenuCategory(
                self._db_location,
                category_uuid=self.menu_category_uuid,
                category_id=self.menu_category_id)
        return self._menu_category

    @property
    def actual_cost(self):
        "Returns a floating-point cost for the menu item"
        return self.db_details['ZACTUALCOST']

    @property
    def approx_cooking_time(self):
        "Returns an approximate cooking time as a floating point number"
        return self.db_details['ZAPPROXCOOKINGTIME']

    @property
    def created_date(self):
        "Returns a tz-aware datetime object for when the menu item was created"
        try:
            return cocoa_2_datetime(self.db_details['ZCREATEDATE'])
        except TypeError:
            return None

    @property
    def count(self):
        "Returns a count of the menu item (inventory), as a floating point #"
        return self.db_details['ZI_COUNT']

    @property
    def warn_count(self):
        "Returns a count below which a low-stock warning should be issued"
        return self.db_details['ZI_WARNCOUNT']

    @property
    def price(self):
        "Returns a price for the menu item, as a floating point number"
        return self.db_details['ZI_PRICE']

    @property
    def version(self):
        """Returns a tz-aware datetime object representing a version for the
        item"""
        return cocoa_2_datetime(self.db_details['ZVERSION'])

    @property
    def full_image(self):
        "Returns a name for the full-sized image associated with the item"
        return self.db_details['ZI_FULLIMAGE']

    @property
    def thumb_image(self):
        "Returns a name for the thumbnail image associated with the item"
        return self.db_details['ZI_THUMBIMAGE']

    @property
    def description(self):
        "Returns a text description of the menu item"
        return self.db_details['ZITEMDESCRIPTION']

    @property
    def parent_uuid(self):
        "Returns a UUID for a parent menu item (for edited/versioned items)"
        return self.db_details['ZI_PARENTUUID']

    @property
    def name(self):
        "Returns the name of the menu item"
        return self.db_details['ZNAME']

    @property
    def public_menu_cloud_image_full_url(self):
        "Returns a url to the public cloud menu full-sized image"
        return self.db_details['ZPUBLICMENUCLOUDIMAGEFULLURL']

    @property
    def public_menu_cloud_image_thumb_url(self):
        "Returns a url to the public cloud menu thumbnail image"
        return self.db_details['ZPUBLICMENUCLOUDIMAGETHUMBNAILURL']

    @property
    def recipe(self):
        "Returns the recipe id (uuid?) associated with the menu item"
        return self.db_details['ZRECIPE']

    @property
    def short_name(self):
        "Returns the short (chit) name of the menu item, if set"
        return self.db_details['ZSHORTNAME']

    @property
    def upc(self):
        "Returns the upc code for the menu item"
        return self.db_details['ZUPC']

    @property
    def db_details(self):
        "Returns cached results for the :attr:`QUERY` specified above"
        if self._db_details is None:
            self._db_details = dict()
            result = self._fetch_entry()
            for key in result.keys():
                # perform the dict copy
                self._db_details[key] = result[key]
        return self._db_details

    def summary(self):
        """Returns a dictionary version of the change"""
        output = {'meta': dict(), 'menu_category': dict(),
                  'sales_category': dict()}
        for attr in self.META_ATTRIBUTES:
            output['meta'][attr] = getattr(self, attr)
        output['menu_category'] = self.menu_category.summary()
        output['sales_category'] = self.sales_category.summary()
        return output

    def _fetch_entry(self):
        """Returns the db row for this menuitem entry"""
        bindings = {
            'menuitem_uuid': self.menuitem_uuid}
        return self.db_handle.cursor().execute(
            self.QUERY, bindings
        ).fetchone()

    def __str__(self):
        "Return a string-formatted version of this change"
        summary = self.summary()
        output = "MenuItem(\n"
        for attr in self.META_ATTRIBUTES:
            output += f"  {attr}: {summary[attr]}\n"
        output += ")"
        return output


class MenuCategory(Sync7Shifts2Sqlite):
    """This class represents a menu category from the ZMENUCATEGORY table

    kwargs:

        - category_uuid: a uuid for the menu category
    """

    #: These attributes will be part of the dictionary representation
    #: of this object, as well as the string version.
    META_ATTRIBUTES = ['category_uuid', 'category_id', 'name', 'course',
                       'custom', 'index', 'sorting', 'tax1', 'tax2', 'tax3',
                       'hidden', 'show_in_public_menu', 'sales_category_id',
                       'hidden_schedule_id', 'kitchen_display_id',
                       'printer_id', 'station_id', 'created_date', 'image']

    #: Query to get details about this object by UUID
    QUERY_BY_UUID = """SELECT
            *
        FROM ZMENUCATEGORY
        WHERE ZUUID = :value
        """

    #: Query to get details about this object by integer key
    QUERY_BY_ID = """SELECT
            *
        FROM ZMENUCATEGORY
        WHERE Z_PK = :value
        """

    def __init__(self, db_location, **kwargs):
        super(MenuCategory, self).__init__(db_location, **kwargs)
        self.log = logging.getLogger("{}.{}".format(
            self.__class__.__module__, self.__class__.__name__
        ))
        self._db_details = kwargs.get('db_details', None)

    @property
    def category_uuid(self):
        "Returns the UUID for this category"
        return self.db_details['ZUUID']

    @property
    def category_id(self):
        "Returns the Z_PK primary key for the menu category"
        return self.db_details['Z_PK']

    @property
    def course(self):
        "Returns the integer course number for the menu category"
        return self.db_details['ZI_COURSE']

    @property
    def custom(self):
        "Returns True if this is a custom menu category"
        return self.db_details['ZI_CUSTOM']

    @property
    def index(self):
        "Returns the index number for the menu category (in a menu)"
        return self.db_details['ZI_INDEX']

    @property
    def sorting(self):
        "Returns an integer representing sorting (True/False?)"
        return self.db_details['ZI_SORTING']

    @property
    def tax1(self):
        "Returns True if the menu category is subject to Tax 1"
        return self.db_details['ZI_TAX1']

    @property
    def tax2(self):
        "Returns True if the menu category is subject to Tax 2"
        return self.db_details['ZI_TAX2']

    @property
    def tax3(self):
        "Returns True if the menu category is subject to Tax 3"
        return self.db_details['ZI_TAX3']

    @property
    def hidden(self):
        "Returns True if the menu item should be hidden"
        return self.db_details['ZISHIDDEN']

    @property
    def show_in_public_menu(self):
        "Returns True if the menu item should be shown in the public menu"
        return self.db_details['ZSHOWINPUBLICMENU']

    @property
    def sales_category_id(self):
        "Returns the sales category as an integer ID"
        return self.db_details['ZTYPE']

    @property
    def sales_category(self):
        "Returns a sales category object for the menu category"
        pass

    @property
    def hidden_schedule_id(self):
        """Returns an integer id for a hidden schedule associated with the
        category"""
        return self.db_details['ZHIDDENSCHEDULE']

    @property
    def kitchen_display_id(self):
        """Returns an integer id for a kitchen display associated with the
        category"""
        return self.db_details['ZKITCHENDISPLAY']

    @property
    def printer_id(self):
        """Returns an integer id for kitchen printer associated with the
        category"""
        return self.db_details['ZPRINTER']

    @property
    def station_id(self):
        """Returns an integer id for the station associated with the
        category"""
        return self.db_details['ZSTATION']

    @property
    def created_date(self):
        "Returns a tz-aware datetime object for when the menu item was created"
        try:
            return cocoa_2_datetime(self.db_details['ZCREATEDATE'])
        except TypeError:
            return None

    @property
    def image(self):
        "Returns a name for the full-sized image associated with the category"
        return self.db_details['ZI_IMAGE']

    @property
    def name(self):
        "Returns the name of the menu item"
        return self.db_details['ZNAME']

    @property
    def db_details(self):
        "Returns cached results for the :attr:`QUERY` specified above"
        if self._db_details is None:
            self._db_details = dict()
            result = self._fetch_entry()
            for key in result.keys():
                # perform the dict copy
                self._db_details[key] = result[key]
        return self._db_details

    def summary(self):
        """Returns a dictionary version of the change"""
        output = dict()
        for attr in self.META_ATTRIBUTES:
            output[attr] = getattr(self, attr)
        return output

    def _fetch_entry(self):
        """Returns the db row for this menuitem entry"""
        bindings = dict()
        if self.kwargs.get('category_uuid', None):
            bindings['value'] = self.kwargs.get('category_uuid')
            return self.db_handle.cursor().execute(
                self.QUERY_BY_UUID, bindings).fetchone()
        if self.kwargs.get('category_id', None):
            bindings['value'] = self.kwargs.get('category_id')
            return self.db_handle.cursor().execute(
                self.QUERY_BY_ID, bindings).fetchone()
        return None

    def __str__(self):
        "Return a string-formatted version of this change"
        summary = self.summary()
        output = "MenuCategory(\n"
        for attr in self.META_ATTRIBUTES:
            output += f"  {attr}: {summary[attr]}\n"
        output += ")"
        return output
