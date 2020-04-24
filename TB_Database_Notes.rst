GENERAL INFO
============
Most tables have a Z_PK field to define a primary key in an auto-increment
form, though auto-increment is not used in the DB (see Z_PRIMARYKEY table).
When joining between tables, Z_PK is almost always used.

Foreign key columns are often named ZI_[SOMETHING], with the 'I' representing
an incremented key (I'm inferring this from the data).

Dates are not in a logical unixtime format natively
supported by Sqlite3 and all other open source databases. Instead they are in
Apple's Epoch Time (from Cocoa framework), so conversion is necessary.

- 1 January 2001 GMT is 0.0
- Every second afterward adds 1 to the number.
- Decimals are partial seconds.
- Conversion to unixtime is to add 978307200 seconds.

TABLE INFORMATION
=================

ZPAIDORDER
----------
This is a central table in the TouchBistro DB architecture. It links many
different tables together through foreign key relationships, such as linking
orders to bills.

Schema::

    CREATE TABLE ZPAIDORDER (
        Z_PK INTEGER PRIMARY KEY,
        Z_ENT INTEGER,
        Z_OPT INTEGER,
        ZI_BILLNUMBER INTEGER,
        ZI_GRATUITYBEFORETAX INTEGER,
        ZI_GROUPNUMBER INTEGER,
        ZI_PARTYSIZE INTEGER,
        ZI_SPLIT INTEGER,
        ZI_TAKEOUTTYPE INTEGER,
        ZI_TAX2ONTAX1 INTEGER,
        ZMAXSEATCOUNT INTEGER,
        ZSECTIONID INTEGER,
        ZSYNCSTATUS INTEGER,
        ZBILLRANGE INTEGER,
        ZCLOSEDTAKEOUT INTEGER,
        ZORDER INTEGER,
        ZPAYMENTS INTEGER,
        ZTABLEORDER INTEGER,
        ZWAITER INTEGER,
        Z75I_PAIDORDERS INTEGER,
        ZI_GRATUITY FLOAT,
        ZI_REDUCEDTAX1 FLOAT,
        ZI_REDUCEDTAX1BILLAMOUNT FLOAT,
        ZI_REDUCEDTAX2 FLOAT,
        ZI_REDUCEDTAX2BILLAMOUNT FLOAT,
        ZI_REDUCEDTAX3 FLOAT,
        ZI_REDUCEDTAX3BILLAMOUNT FLOAT,
        ZI_SPLITBY FLOAT,
        ZI_TAX1 FLOAT,
        ZI_TAX2 FLOAT,
        ZI_TAX3 FLOAT,
        ZLOYALTYCREDITBALANCE FLOAT,
        ZLOYALTYPOINTSBALANCE FLOAT,
        ZLOYALTYPOINTSEARNED FLOAT,
        ZLOYALTYPOINTSREFUNDED FLOAT,
        ZLOYALTYPOINTSUSED FLOAT,
        ZOUTSTANDINGBALANCE FLOAT,
        ZPAYDATE TIMESTAMP,
        ZSEATEDDATE TIMESTAMP,
        ZADDRESS VARCHAR,
        ZBILLRANGEUUID VARCHAR,
        ZBUSINESSNUMBER VARCHAR,
        ZCITY VARCHAR,
        ZCLOSEDATVERSION VARCHAR,
        ZCOUNTRY VARCHAR,
        ZCUSTOMERID VARCHAR,
        ZEMAIL VARCHAR,
        ZLOYALTYACCOUNTNAME VARCHAR,
        ZNAME VARCHAR,
        ZORIGINALPAIDORDERUUID VARCHAR,
        ZPARTYNAME VARCHAR,
        ZPARTYUUID VARCHAR,
        ZRESTAURANTDESCRIPTION VARCHAR,
        ZSECTION VARCHAR,
        ZSTATE VARCHAR,
        ZSYNCEDATVERSION VARCHAR,
        ZTABLENAME VARCHAR,
        ZTAX1NUMBER VARCHAR,
        ZTAX2NUMBER VARCHAR,
        ZTAX3NUMBER VARCHAR,
        ZTELEPHONE VARCHAR,
        ZTHANKSINFO VARCHAR,
        ZUUID VARCHAR,
        ZWAITERUUID VARCHAR,
        ZWEBSITE VARCHAR,
        ZZIP VARCHAR );
    CREATE INDEX ZPAIDORDER_ZBILLRANGE_INDEX ON ZPAIDORDER (ZBILLRANGE);
    CREATE INDEX ZPAIDORDER_ZCLOSEDTAKEOUT_INDEX ON ZPAIDORDER (ZCLOSEDTAKEOUT);
    CREATE INDEX ZPAIDORDER_ZORDER_INDEX ON ZPAIDORDER (ZORDER);
    CREATE INDEX ZPAIDORDER_ZPAYMENTS_INDEX ON ZPAIDORDER (ZPAYMENTS);
    CREATE INDEX ZPAIDORDER_ZTABLEORDER_INDEX ON ZPAIDORDER (ZTABLEORDER);
    CREATE INDEX ZPAIDORDER_ZWAITER_INDEX ON ZPAIDORDER (ZWAITER);
    CREATE INDEX ZPAIDORDER_Z75I_PAIDORDERS_INDEX ON ZPAIDORDER (Z75I_PAIDORDERS);
    CREATE INDEX Z_PaidOrder_uuid ON ZPAIDORDER (ZUUID COLLATE BINARY ASC);

Example SQL query::

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
different key, likely because orders can have splits.

ZPAYMENTS is a reference to the ZPAYMENTS table (Z_PK).

Z_CLOSEDTAKEOUT
---------------
- Row per takeout order, including bar tabs and deliveries.
- This is where you'll find a foreign key to ZCUSTOMTAKEOUTYPE (Z_PK)

Z_CUSTOMTAKEOUTTYPE
-------------------
- Defines custom takeout types (ZNAME is helpful here)

PUTTING IT ALL TOGETHER
=======================

Get a list of paid orders for April 2, 2020 in MDT::

    SELECT
        (ZPAIDORDER.ZPAYDATE + 978307200) as EpochDate,
        (ZPAYMENT.ZI_AMOUNT + 0.0) as Amount
    FROM ZPAIDORDER
    LEFT JOIN ZPAYMENT ON ZPAYMENT.ZPAYMENTGROUP = ZPAIDORDER.ZPAYMENTS
    WHERE
        ZPAIDORDER.ZPAYDATE >= 607500000.0 AND
        ZPAIDORDER.ZPAYDATE < 607586400.0;

In code::

    import os
    import touchbistro.paidorder
    foo = touchbistro.paidorder.PaidOrderSummary(
        os.environ.get('TB_DB_PATH'),
        earliest=607500000.0, cutoff=607586400.0)
    for row in foo.summary():
    print("{}: {}".format(row['EpochDate'], row['Amount']))