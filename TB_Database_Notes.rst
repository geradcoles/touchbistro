GENERAL INFO
============
Most tables have a Z_PK field to define a primary key in an auto-increment
form, though auto-increment is not used in the DB (see Z_PRIMARYKEY table).
When joining between tables, Z_PK is almost always used.

Foreign key columns are usually named ZI_[SOMETHING], with the 'I' representing
an incremented foreign key (I'm inferring this from the data).

Dates are not in a logical unixtime format or javascript date format natively
supported by Sqlite3 and all other open source databases. Instead they are in
Apple's Epoch Time (from Cocoa framework).
- 1 January 2001 GMT is 0.0
- Every second afterward adds 1 to the number.
- Decimals are partial seconds.
- Conversion to unixtime is to add 31 years' worth of seconds
  (31 * 60 * 60 * 24 * 365) = 977616000 seconds.
  (Leap years don't affect unixtime)

ZPAIDORDER
==========
# View closed bills
SELECT
    Z_PK,
    ZI_BILLNUMBER,
    ZI_TAKEOUTTYPE,
    ZCLOSEDTAKEOUT,
    ZORDER,
    ZPAYMENTS,
    ZPAYDATE,
    ZSEATEDDATE
    FROM ZPAIDORDER
    WHERE Z_BILLNUMBER=12345;

ZI_TAKEOUTTYPE is the equivalent of an ENUM:
- Blank = a regular, dine-in order
- 0 = Takeout (including custom types)
- 1 = Delivery
- 2 = Bar Tab

Z_PK and ZI_BILLNUMBER are usually the same.

ZCLOSEDTAKEOUT is a foreign key to Z_CLOSEDTAKEOUT (Z_PK).

ZORDER is not the same as the order id for the order. It appears to be a
different key.

ZPAYMENTS is a reference to the ZPAYMENTS table (Z_PK).

Z_CLOSEDTAKEOUT
===============
- Row per takeout order, including bar tabs and deliveries.
- This is where you'll find a foreign key to ZCUSTOMTAKEOUTYPE (Z_PK)

Z_CUSTOMTAKEOUTTYPE
===================
- Defines custom takeout types (ZNAME is helpful here)

