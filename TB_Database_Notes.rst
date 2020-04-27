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

ZMENUITEM
---------

Schema::

    CREATE TABLE ZMENUITEM (
        Z_PK INTEGER PRIMARY KEY,
        Z_ENT INTEGER,
        Z_OPT INTEGER,
        ZBACKGROUNDCOLOR INTEGER,
        ZI_COURSE INTEGER,
        ZI_EXCLUDETAX1 INTEGER,
        ZI_EXCLUDETAX2 INTEGER,
        ZI_EXCLUDETAX3 INTEGER,
        ZI_HIDDEN INTEGER,
        ZI_INDEX INTEGER,
        ZI_WINEID INTEGER,
        ZINSTOCK INTEGER,
        ZISARCHIVED INTEGER,
        ZISRETURNABLE INTEGER,
        ZPRINTSEPERATECHIT INTEGER,
        ZREQUIREMANAGER INTEGER,
        ZSHOWINPUBLICMENU INTEGER,
        ZTYPE INTEGER,
        ZUSERECIPECOST INTEGER,
        ZUSEDFORGIFTCARDS INTEGER,
        ZCATEGORY INTEGER,
        ZREQUIRESVALIDATIONONKIOSK INTEGER,
        ZRESTAURANT INTEGER,
        ZACTUALCOST FLOAT,
        ZAPPROXCOOKINGTIME FLOAT,
        ZCREATEDATE TIMESTAMP,
        ZI_COUNT FLOAT,
        ZI_PRICE FLOAT,
        ZI_WARNCOUNT FLOAT,
        ZVERSION TIMESTAMP,
        ZCATEGORYNAME VARCHAR,
        ZCATEGORYUUID VARCHAR,
        ZI_FULLIMAGE VARCHAR,
        ZI_PARENTUUID VARCHAR,
        ZI_THUMBIMAGE VARCHAR,
        ZITEMDESCRIPTION VARCHAR,
        ZNAME VARCHAR,
        ZPUBLICMENUCLOUDIMAGEFULLURL VARCHAR,
        ZPUBLICMENUCLOUDIMAGETHUMBNAILURL VARCHAR,
        ZRECIPE VARCHAR,
        ZSHORTNAME VARCHAR,
        ZUPC VARCHAR,
        ZUUID VARCHAR );


ZORDERITEM
----------

Schema::

    CREATE TABLE ZORDERITEM (
        Z_PK INTEGER PRIMARY KEY,
        Z_ENT INTEGER,
        Z_OPT INTEGER,
        ZI_COURSE INTEGER,
        ZI_INDEX INTEGER,
        ZI_SEND INTEGER,
        ZI_SENT INTEGER,
        ZISRETURN INTEGER,
        ZMENUITEM INTEGER,
        ZMENUPAGE INTEGER,
        ZCREATEDATE TIMESTAMP,
        ZI_OPENPRICE FLOAT,
        ZI_QUANTITY FLOAT,
        ZMENUITEMCOST FLOAT,
        ZONLINEORDERPRICE FLOAT,
        ZRECIPECOST FLOAT,
        ZSENTTIME TIMESTAMP,
        ZMENUITEMUUID VARCHAR,
        ZUUID VARCHAR,
        ZWAITERID VARCHAR );

ZMENUITEMUUID is the uuid of the menu item.

ZWAITERID is the uuid of the staff member.


ZORDERITEMLOG
-------------

Contains a record of each item that was part of an order.

Schema::

    CREATE TABLE ZORDERITEMLOG (
        Z_PK INTEGER PRIMARY KEY,
        Z_ENT INTEGER,
        Z_OPT INTEGER,
        ZCREATEDATE TIMESTAMP,
        ZMENUITEMVERSION TIMESTAMP,
        ZORDERITEMCREATEDATE TIMESTAMP,
        ZQUANTITY FLOAT,
        ZTOTALPRICEWITHMODIFIERS FLOAT,
        ZMANAGER VARCHAR,
        ZMENUITEM VARCHAR,
        ZORDERNUMBER VARCHAR,
        ZUUID VARCHAR,
        ZWAITER VARCHAR );

ZMENUITEM contains the UUID of the menu item.

ZORDERNUMBER is the customer-facing order ID.

ZWAITER is the UUID of the staff member.

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

ZI_TAX1 is a percentage of tax on the amount (aka 0.05 for GST).

ZCLOSEDTAKEOUT is a foreign key to table Z_CLOSEDTAKEOUT (Z_PK).

ZORDER is not the same as the order id for the order. It appears to be a
different key, likely because orders can have splits.

ZPAYMENTS is a reference to the ZPAYMENTS table (Z_PK).

ZORDER
------

Schema::

    CREATE TABLE ZORDER (
        Z_PK INTEGER PRIMARY KEY,
        Z_ENT INTEGER,
        Z_OPT INTEGER,
        ZBILLNUMBER INTEGER,
        ZI_EXCLUDETAX1 INTEGER,
        ZI_EXCLUDETAX2 INTEGER,
        ZI_EXCLUDETAX3 INTEGER,
        ZI_INDEX INTEGER,
        ZPAIDORDER INTEGER,
        ZPARTY INTEGER,
        ZPARTYASSPLITORDER INTEGER,
        ZTEMPPARTY INTEGER,
        ZCREATEDATE TIMESTAMP,
        ZI_SPLITBY FLOAT,
        ZGROUPCOLORHEXSTRING VARCHAR,
        ZNOTE VARCHAR,
        ZORDERNUMBER VARCHAR,
        ZUUID VARCHAR,
        ZLOYALTYTRANSACTIONXREFID VARCHAR);
    CREATE INDEX ZORDER_ZPAIDORDER_INDEX ON ZORDER (ZPAIDORDER);
    CREATE INDEX ZORDER_ZPARTY_INDEX ON ZORDER (ZPARTY);
    CREATE INDEX ZORDER_ZPARTYASSPLITORDER_INDEX ON ZORDER (ZPARTYASSPLITORDER);
    CREATE INDEX ZORDER_ZTEMPPARTY_INDEX ON ZORDER (ZTEMPPARTY);
    CREATE INDEX Z_Order_uuid ON ZORDER (ZUUID COLLATE BINARY ASC);

ZPAIDORDER has the foreign key to the ZPAIDORDER table.

ZORDERNUMBER contains the staff-visible order number.

ZPAYMENT
--------

Lists individual payments.

Schema::

    CREATE TABLE ZPAYMENT (
        Z_PK INTEGER PRIMARY KEY,
        Z_ENT INTEGER,
        Z_OPT INTEGER,
        ZI_INDEX INTEGER,
        ZI_TYPE INTEGER,
        ZACCOUNT INTEGER,
        ZCUSTOMER INTEGER,
        ZPAYMENTGATEWAYTRANSACTIONINFO INTEGER,
        ZPAYMENTGROUP INTEGER,
        ZBALANCE FLOAT,
        ZCREATEDATE TIMESTAMP,
        ZI_AMOUNT FLOAT,
        ZI_CHANGE FLOAT,
        ZTIP FLOAT,
        ZAUTH VARCHAR,
        ZCARDEXPIRY VARCHAR,
        ZCARDHOLDER VARCHAR,
        ZCARDNUMBER VARCHAR,
        ZCARDTYPE VARCHAR,
        ZMERCURYRESPONSEBASE64 VARCHAR,
        ZUUID VARCHAR,
        ZI_REFUNDABLEAMOUNT FLOAT,
        ZORIGINALPAYMENTUUID VARCHAR);
    CREATE INDEX ZPAYMENT_ZACCOUNT_INDEX ON ZPAYMENT (ZACCOUNT);
    CREATE INDEX ZPAYMENT_ZCUSTOMER_INDEX ON ZPAYMENT (ZCUSTOMER);
    CREATE INDEX ZPAYMENT_ZPAYMENTGATEWAYTRANSACTIONINFO_INDEX ON ZPAYMENT (ZPAYMENTGATEWAYTRANSACTIONINFO);
    CREATE INDEX ZPAYMENT_ZPAYMENTGROUP_INDEX ON ZPAYMENT (ZPAYMENTGROUP);
    CREATE INDEX Z_Payment_uuid ON ZPAYMENT (ZUUID COLLATE BINARY ASC);

ZI_TYPE appears to be an enum-like value.

- 0 = Cash
- 1 = Electronic payment including Loyalty Card and custom manual payment types
- 4 = Customer Account

ZACCOUNT is foreign key to ZTBACCOUNT (Z_PK).

ZCUSTOMER appears to be blank for customer account payments.

ZPAYMENTGROUP is a foreign key to ZPAYMENTS (Z_PK).

ZI_AMOUNT is the dollar amount of the transaction.

ZI_CHANGE is the change given.

ZTIP is the amount of any tips rung in.

ZAUTH is the auth number for the transaction, when present.

ZPAYMENTS
---------

This table lists all payments for for a given order ID (from the ZPAIDORDER
table). A quick lookup table, not necessary when using joins, but good for
subselects.

ZTBACCOUNT
----------

A list of customer accounts.

ZBALANCE is the current account balance (inverted value as it is a debt).

ZNAME is the customer name.

ZNOTE is the account notes field.

ZNUMBER is the phone number associated with the account.

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
        (ZPAIDORDER.ZPAYDATE + 978307200) as Timestamp,
        ZPAIDORDER.ZI_BILLNUMBER as Bill,
        ZPAIDORDER.ZI_TAKEOUTTYPE as Order_Type,
        ZPAYMENT.ZCARDTYPE as Payment_Type,
        ifnull(round(ZPAYMENT.ZI_AMOUNT, 2), 0.0) as Payments,
        ifnull(round(ZPAYMENT.ZTIP, 2), 0.0) as Total_Tips
    FROM ZPAIDORDER
    LEFT JOIN ZPAYMENT ON ZPAYMENT.ZPAYMENTGROUP = ZPAIDORDER.ZPAYMENTS
    WHERE
        ZPAIDORDER.ZPAYDATE >= 607500000.0 AND
        ZPAIDORDER.ZPAYDATE < 607586400.0;
