"""This module provides classes and methods for viewing and reporting on menu
items in TouchBistro"""
from .base import TouchBistroDBObject
from .dates import cocoa_2_datetime
from .changelog import ChangeLogEntry
from .salescategory import SalesCategoryByID


class MenuChangeLogEntry(ChangeLogEntry):
    """This class overrides changelog.ChangeLogEntry to provide helpers for
    obtaining more details about menu changes, such as Waiter and menu item
    info.

    kwargs:

        - changelog_uuid: a uuid for the changelog entry
    """

    #: These attributes will be part of the dictionary representation
    #: of this object, as well as the string version.
    META_ATTRIBUTES = ['uuid', 'change_id', 'timestamp',
                       'change_type', 'change_type_details',
                       'object_reference',
                       'object_reference_type', 'user_uuid',
                       'value_changed_from', 'value_changed_to']

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


class MenuItem(TouchBistroDBObject):
    """This class represents a menu item from the ZMENUITEM table.

    kwargs:

        - menuitem_uuid: a uuid for the menuitem
    """

    #: These attributes will be part of the dictionary representation
    #: of this object, as well as the string version.
    META_ATTRIBUTES = ['uuid', 'menu_id', 'course', 'hidden', 'index',
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

    QUERY_BINDING_ATTRIBUTES = ['menuitem_uuid']

    def __init__(self, db_location, **kwargs):
        super(MenuItem, self).__init__(db_location, **kwargs)
        self._menu_category = None
        self._sales_category = None

    @property
    def menu_id(self):
        "Returns the Z_PK primary key for the menu item"
        return self.db_results['Z_PK']

    @property
    def course(self):
        "Returns the integer course number for the menu item (if set)"
        return self.db_results['ZI_COURSE']

    @property
    def exclude_tax1(self):
        "Returns True if the menu item is excluded from Tax 1"
        return self.db_results['ZI_EXCLUDETAX1']

    @property
    def exclude_tax2(self):
        "Returns True if the menu item is excluded from Tax 2"
        return self.db_results['ZI_EXCLUDETAX2']

    @property
    def exclude_tax3(self):
        "Returns True if the menu item is excluded from Tax 3"
        return self.db_results['ZI_EXCLUDETAX3']

    @property
    def hidden(self):
        "Returns True if the menu item should be hidden"
        return self.db_results['ZI_HIDDEN']

    @property
    def index(self):
        "Returns the index number for the menu item (in a menu category)"
        return self.db_results['ZI_INDEX']

    @property
    def in_stock(self):
        "Returns True if the menu item is in stock"
        return self.db_results['ZINSTOCK']

    @property
    def is_archived(self):
        "Returns True if the menu item is archived (deleted)"
        return self.db_results['ZISARCHIVED']

    @property
    def is_returnable(self):
        "Returns True if the menu item is returnable"
        return self.db_results['ZISRETURNABLE']

    @property
    def print_seperate_chit(self):
        "Returns True if the menu item should be printed on its own chit"
        return self.db_results['ZPRINTSEPERATECHIT']

    @property
    def require_manager(self):
        "Returns True if the menu item requires a manager to order"
        return self.db_results['ZREQUIREMANAGER']

    @property
    def show_in_public_menu(self):
        "Returns True if the menu item should be shown in the public menu"
        return self.db_results['ZSHOWINPUBLICMENU']

    @property
    def sales_category_type_id(self):
        "Returns the sales category type as an integer ID"
        return self.db_results['ZTYPE']

    @property
    def sales_category(self):
        "Returns a sales category object for the menu item"
        if self._sales_category is None:
            self._sales_category = SalesCategoryByID(
                self._db_location,
                sales_type_id=self.sales_category_type_id)
        return self._sales_category

    @property
    def use_recipe_cost(self):
        "Returns True if the menu item should be costed based on a recipe"
        return self.db_results['ZUSERECIPECOST']

    @property
    def used_for_gift_cards(self):
        "Returns True if the menu item is used to purchase gift cards"
        return self.db_results['ZUSEDFORGIFTCARDS']

    @property
    def menu_category_id(self):
        "Returns the menu category id associated with this menu item"
        return self.db_results['ZCATEGORY']

    @property
    def menu_category_uuid(self):
        "Returns the menu category uuid associated with this menu item"
        return self.db_results['ZCATEGORYUUID']

    @property
    def menu_category(self):
        "Returns a MenuCategory object corresponding to the menu item"
        if self._menu_category is None:
            if self.menu_category_uuid:
                self._menu_category = MenuCategory(
                    self._db_location,
                    category_uuid=self.menu_category_uuid)
            else:
                self._menu_category = MenuCategoryByID(
                    self._db_location,
                    category_id=self.menu_category_id)
        return self._menu_category

    @property
    def actual_cost(self):
        "Returns a floating-point cost for the menu item"
        return self.db_results['ZACTUALCOST']

    @property
    def approx_cooking_time(self):
        "Returns an approximate cooking time as a floating point number"
        return self.db_results['ZAPPROXCOOKINGTIME']

    @property
    def created_date(self):
        "Returns a tz-aware datetime object for when the menu item was created"
        try:
            return cocoa_2_datetime(self.db_results['ZCREATEDATE'])
        except TypeError:
            return None

    @property
    def count(self):
        "Returns a count of the menu item (inventory), as a floating point #"
        return self.db_results['ZI_COUNT']

    @property
    def warn_count(self):
        "Returns a count below which a low-stock warning should be issued"
        return self.db_results['ZI_WARNCOUNT']

    @property
    def price(self):
        "Returns a price for the menu item, as a floating point number"
        return self.db_results['ZI_PRICE']

    @property
    def version(self):
        """Returns a tz-aware datetime object representing a version for the
        item"""
        return cocoa_2_datetime(self.db_results['ZVERSION'])

    @property
    def full_image(self):
        "Returns a name for the full-sized image associated with the item"
        return self.db_results['ZI_FULLIMAGE']

    @property
    def thumb_image(self):
        "Returns a name for the thumbnail image associated with the item"
        return self.db_results['ZI_THUMBIMAGE']

    @property
    def description(self):
        "Returns a text description of the menu item"
        return self.db_results['ZITEMDESCRIPTION']

    @property
    def parent_uuid(self):
        "Returns a UUID for a parent menu item (for edited/versioned items)"
        return self.db_results['ZI_PARENTUUID']

    @property
    def name(self):
        "Returns the name of the menu item"
        return self.db_results['ZNAME']

    @property
    def public_menu_cloud_image_full_url(self):
        "Returns a url to the public cloud menu full-sized image"
        return self.db_results['ZPUBLICMENUCLOUDIMAGEFULLURL']

    @property
    def public_menu_cloud_image_thumb_url(self):
        "Returns a url to the public cloud menu thumbnail image"
        return self.db_results['ZPUBLICMENUCLOUDIMAGETHUMBNAILURL']

    @property
    def recipe(self):
        "Returns the recipe id (uuid?) associated with the menu item"
        return self.db_results['ZRECIPE']

    @property
    def short_name(self):
        "Returns the short (chit) name of the menu item, if set"
        return self.db_results['ZSHORTNAME']

    @property
    def upc(self):
        "Returns the upc code for the menu item"
        return self.db_results['ZUPC']

    def summary(self):
        """Returns a dictionary version of the change"""
        output = super(MenuItem, self).summary()
        output['menu_category'] = self.menu_category.summary()
        output['sales_category'] = self.sales_category.summary()
        return output


class MenuCategory(TouchBistroDBObject):
    """This class represents a menu category from the ZMENUCATEGORY table

    kwargs:

        - category_uuid: a uuid for the menu category
    """

    #: These attributes will be part of the dictionary representation
    #: of this object, as well as the string version.
    META_ATTRIBUTES = ['uuid', 'category_id', 'name', 'course',
                       'custom', 'index', 'sorting', 'tax1', 'tax2', 'tax3',
                       'hidden', 'show_in_public_menu',
                       'sales_category_type_id',
                       'hidden_schedule_id', 'kitchen_display_id',
                       'printer_id', 'station_id', 'created_date', 'image']

    #: Query to get details about this object by UUID
    QUERY = """SELECT
            *
        FROM ZMENUCATEGORY
        WHERE ZUUID = :category_uuid
        """

    QUERY_BINDING_ATTRIBUTES = ['category_uuid']

    def __init__(self, db_location, **kwargs):
        super(MenuCategory, self).__init__(db_location, **kwargs)
        self._sales_category = None

    @property
    def category_id(self):
        "Returns the Z_PK primary key for the menu category"
        return self.db_results['Z_PK']

    @property
    def course(self):
        "Returns the integer course number for the menu category"
        return self.db_results['ZI_COURSE']

    @property
    def custom(self):
        "Returns True if this is a custom menu category"
        return self.db_results['ZI_CUSTOM']

    @property
    def index(self):
        "Returns the index number for the menu category (in a menu)"
        return self.db_results['ZI_INDEX']

    @property
    def sorting(self):
        "Returns an integer representing sorting (True/False?)"
        return self.db_results['ZI_SORTING']

    @property
    def tax1(self):
        "Returns True if the menu category is subject to Tax 1"
        return self.db_results['ZI_TAX1']

    @property
    def tax2(self):
        "Returns True if the menu category is subject to Tax 2"
        return self.db_results['ZI_TAX2']

    @property
    def tax3(self):
        "Returns True if the menu category is subject to Tax 3"
        return self.db_results['ZI_TAX3']

    @property
    def hidden(self):
        "Returns True if the menu item should be hidden"
        return self.db_results['ZISHIDDEN']

    @property
    def show_in_public_menu(self):
        "Returns True if the menu item should be shown in the public menu"
        return self.db_results['ZSHOWINPUBLICMENU']

    @property
    def sales_category_type_id(self):
        "Returns the sales category as an integer ID"
        return self.db_results['ZTYPE']

    @property
    def sales_category(self):
        "Returns a sales category object for the menu category"
        if self._sales_category is None:
            self._sales_category = SalesCategoryByID(
                self._db_location,
                sales_type_id=self.sales_category_type_id)
        return self._sales_category

    @property
    def hidden_schedule_id(self):
        """Returns an integer id for a hidden schedule associated with the
        category"""
        return self.db_results['ZHIDDENSCHEDULE']

    @property
    def kitchen_display_id(self):
        """Returns an integer id for a kitchen display associated with the
        category"""
        return self.db_results['ZKITCHENDISPLAY']

    @property
    def printer_id(self):
        """Returns an integer id for kitchen printer associated with the
        category"""
        return self.db_results['ZPRINTER']

    @property
    def station_id(self):
        """Returns an integer id for the station associated with the
        category"""
        return self.db_results['ZSTATION']

    @property
    def created_date(self):
        "Returns a tz-aware datetime object for when the menu item was created"
        try:
            return cocoa_2_datetime(self.db_results['ZCREATEDATE'])
        except TypeError:
            return None

    @property
    def image(self):
        "Returns a name for the full-sized image associated with the category"
        return self.db_results['ZI_IMAGE']

    @property
    def name(self):
        "Returns the name of the menu item"
        return self.db_results['ZNAME']


class MenuCategoryByID(MenuCategory):
    """Use this class to get a menu category starting from its Z_PK primary key
    rather than UUID.

    kwargs:

        - category_id: the Z_PK category id for the Menu Category
    """

    #: Query to get details about this object by integer key
    QUERY = """SELECT
            *
        FROM ZMENUCATEGORY
        WHERE Z_PK = :category_id
        """

    QUERY_BINDING_ATTRIBUTES = ['category_id']
