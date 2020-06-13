TouchBistro Database Python Library
===================================

This library provides command line tools and libraries for reading a
TouchBistro Sqlite3 database, and grants the user the ability to view
data and create reports that are not currently available in the cloud. The core
concept of this module is to surface as much data as possible, and do it in a
way that is suitable for reporting with tools like Excel or Google Sheets, or
for further programmatic processing and possibly output to other systems (such
as accounting software). The most robust and useful portion of this tool is the
``order report`` command, which dumps the following for every order:

- All the metadata surrounding an order, such as its number, bill number,
  waiter, type (dine-in, takeout, etc), payment time, subtotal, taxes, and
  amount, as well as party-level information (seats, party name).
- A breakdown of every line item on the order (as separate spreadsheet rows or
  json structures), with menu item information such as sales category, pricing,
  quantity, name and price. The waiter who actually rung in the menu item
  is also included.
- A further breakdown of every modifier applied to each line-item, including
  the same core fields as for the base menu item, such as sales categories for
  menu-based and text-based modifiers.
- Discounts applied to each line-item, broken down by sales categories when
  modifiers have a different category than base menu items. Includes information
  about the waiter(s) who both applied and authorized the discount.
- Payment records for the order, including details about the class of payment
  (cash/electronic), custom payment types, tip amounts, change given, etc.
  Multiple payments are supported.

At Prairie Dog Brewing, we use this library to dump TouchBistro data to a
comma-separated-values (CSV) spreadsheet daily (in Google Drive), which our
bookkeeper manually migrates
into a larger Excel spreadsheet (which holds a year's worth of data at the
order line-item level), and runs a combination of pivottables over top of the
data to provide us with a multi-faceted summary of our daily sales that we
use to create daily sales invoices on our accounting platform. This is better
than using the built-in TouchBistro reports because:

1. It is more accurate - correctly handling situations like:
    
- Discounts applied to menu-based modifiers where the sales category does
  not match that of the parent menu item (a TB bug causes the entire discount
  amount to be applied to the parent menu item sales category rather than
  being applied pro-rata to the parent item and its modifiers based on their
  portion of the total line-item amount -- this is especially bad if the
  parent menu item costs less than the modifier and a large discount is
  applied, which could make the parent menu item sales category value go
  negative and be truncated to $0.00 and discount amounts be "lost").
  
- Discounts being applied by a server against another server's open order.
  Often these discounts become lost in End of Day totals or result in
  inaccuracies in cloud reports.

- Orders left open with unpaid balances past day end, which add to sales
  totals on the End of Day report, even without payments. With the ``order
  report`` command output, these orders can quickly be identified by the
  discrepancy between their lack of a "Payment" object or balance differences
  compared to their "OrderById" parent object.

- Deleted discounts sometimes being (incorrectly) synchronized to
  TouchBistro Cloud and causing reporting errors.

2. It provides missing visibility by surfacing data that is absent or difficult
to use in cloud financial reports, like:

- Number of seats/guests (used to calculate average guest check)
- Order types (dine-in, takeout, delivery, bartab, etc)
- Custom takeout types
- Custom payment types
- Discount authorization information (present in the cloud but can't be
  reported on directly, and buggy)
- Loyalty card transactions that did not occur as part of a sale (order),
  such as adding balance.

3. Beyond just surfacing data, doing it so in a format suitable for Excel
pivottables or programmatic access, natively in Python3, or through JSON and
CSV output formats.

4. By dumping order data with dollar amounts from many different object types,
doors are open for validating reported order subtotals by comparing them with
order line item, modifier and discount totals. Further, we can validate
that payment records match order totals (plus tips), and quickly identify
deleted orders with payments, registers with unpaid balances, or bugs with
third party integrations, such as online ordering systems not properly closing
orders.

**IMPORTANT: Always run this tool against a copy of the TouchBistro Sqlite3
database**. Bad things could happen if this report runs queries that lock the
active database while TouchBistro is using it, possibly destroying your
restaurant point of sale.

Installation
------------

Install this program like you would any typical Python module from git::

    git clone git@github.com:geradcoles/touchbistro.git
    cd touchbistro
    pip install -r requirements.txt # uses only standard stuff
    python setup.py install # or develop if you plan on hacking code

Order Report
------------

As already mentioned, the ``order report`` command is the most powerful
in this library, combining the per-order details common with ``order fetch``
below, but doing so en-masse for a specified day or range of days, in any of
the three formats supported (receipt-form, JSON, or CSV). Further, given the
``--with-loyalty`` switch, it will dump a report of all the Loyalty balance
transactions for the given period (with may be duplicates of the transactions
associated with orders), for example::

    $ order report Restaurant.sql 2020-06-01  # for one day
    $ order report Restaurant.sql 2020-06-01 2020-06-30 # many days

We typically run it like this::

    $ order report \
        Restaurant.sql \
        2020-06-01 \
        --csv \
        --with-loyalty \
        --file=output.csv

We use the spreadsheet found in the SPREADSHEETS folder from this project to
report on the output of the command above, copying and pasting all of the rows
from the CSV data above into the RAW DATA worksheet (directly into the table,
which is empty in the version checked into this repository). We continuously
append more data to the end of that table, and then refresh a pivottable on
the SALES SUMMARY worksheet to refresh all data. The sales summary has a time
picker and a slicers to break down the sales by a specific server or sales
category, but this is easily expanded upon by anyone with a strong command of
MS Excel.

Order Fetch
-------------

The ``order fetch`` command is very useful for digging into
the details of orders at a depth not visible in TouchBistro, itself. Item
modifiers and discounts are visible in a receipt-like format with the ``order
fetch`` command used by default (see below). Add the ``-j`` switch for a much
more detailed JSON format, which includes low-level fields about the order,
order line items, modifiers, discounts and payments, including cash,
electronic, customer account, and Loyalty account payments. Gratuities and
partial/multiple payments are supported, as well as refunds.

Here's an example of a command-line invocation of the ``order`` commamnd set
to the default, receipt-like view of an order::

    $ order fetch Restaurant.sql 30031

        ORDER DETAILS FOR ORDER #30031

    Order Date/Time: 	2020-04-22 09:34:13 PM
    Table Name: None	Party Name: Joe
    Bill Number: 40080	Order Type: takeout
    Server Name: Nancy S

    -----------------------------------------------

    Adult Chicken Tenders                  $15.00
    - $7.50: Staff: Joe Discount
                           Item Subtotal:  $7.50

    Popplers                               $7.00
    - $3.50: Staff: Joe Discount
                           Item Subtotal:  $3.50

    Grizzly Paw Black Cherry               $4.00
    - $4.00: Shift Joe Discount
                           Item Subtotal:  $0.00


    -----------------------------------------------
                                Subtotal:  $11.00
                                     Tax:  $0.55
    -----------------------------------------------
                                   TOTAL:  $11.55
    Payment  1: LOYALTY CARD [819]         $11.55
                                     Tip:  $0.00
                       Remaining Balance:  $0.00

    Loyalty Customer: Joe Miller
    Loyalty Credit Balance:  $145.87

As you can see in the above example, the order details are shown at the top,
then line items with any discounts or modifiers, including a broken out 
subtotal per line item, making it easier to understand what's going on with
modifiers and discounts. Next, we have the order subtotal and tax amount,
followed by the order total amount.

The next section of the receipt format contains a list of every payment applied
to the order, in the order that they occurred. The payment type is always
listed immediately after the payment number, and for electronic payment types,
an authorization number is included, followed by the payment amount at the
right-hand side of the view. Below, find the amount of gratuity added to the
payment as "Tip", and the remaining order balance after the payment occurred.

If a Loyalty account was used to pay for the order, the details about the
account, including remaining credit or point balance (depending on what was
used to pay for the order) will be shown at the bottom of the receipt view.
Note that regardless of how many different Loyalty accounts were used to pay
for an order only one account name and balance will show here -- that's because
of the TouchBistro database architecture, which appears to store this vital
info in the ZPAIDORDER table (one record per order) rather than in the ZPAYMENT
table (one record per payment).

The other way to invoke ``order`` is to add the ``--json``, or ``-j`` switch to
the command line, which outputs the same data in a much more verbose JSON
structure. That structure includes details like which waiter added a line item
or discounted it, whether items were sent and at what time, etc. The JSON
structure is extensive and recurses deep into the object hierarchy to provide
maximum detail for debugging or use in other applications.

This can all happen programmatically like this::

    from touchbistro.orders import Order
    order = Order('/path/to/Restaurant.sql', order_number=12345)
    details = order.summary() # get the same dict exposed with --json above
    # OR with methods and attributes like:
    print(order.subtotal())
    for payment in order.payments:
        print(f"Payment {payment.payment_number}: ${payment.amount:3.2f}")


Paid Order Summary
------------------

This was the first tool we wrote for this library, so it is a little less
polished in terms of code and capability compared to ``order``, but you can
use the ``payment`` command to generate a summary of paid orders for a
specified time period like this::

    payments /path/to/Restaurant.sql --from=2020-03-26 --to=2020-04-23

Add the ``--csv`` flag if you plan to use Excel to view or manipulate the data::

    payments /path/to/Restaurant.sql \
        --from=2020-03-26 \
        --to=2020-04-23 \
        --csv > output.csv

Important Caveats
-----------------
This library started entirely as the result of reverse-engineering of the
TouchBistro database by one person. We have had to interpret database column
names and table structures to infer architecture and establish relationships
between rows in many different tables to come up with a surprisingly-complete
view of the objects TouchBistro uses in their software, at least as far as
the objects we require for accounting and reporting purposes.

The downside is that this is totally unsupported software and it could be
rendered inoperable by TouchBistro at any moment due to changes to their
database architecture. As it is, many tables and columns in the TouchBistro
database change names with each software update, so it is difficult to
write code against those tables, and should TouchBistro change their naming
scheme, this code will require updates and continuous maintenance to stay
relevant. **Your mileage may vary!**

Future Improvements and Crowdsourcing
-------------------------------------
Any help maintaining this module is welcome! Keep in mind that we wrote this
library with a specific operational need (and urgency) in mind, so it is
lacking many of the wonderful things we've come to expect from modern Python
modules, like tests, a Sphynx build, etc. CLI commands do not perform any
input validation. Pointing a command at a non-existent path for the Sqlite3
database results in a new one being created there.

There's also a lot of room for
future feature growth, such as elaborating more on waiters, roles and shifts,
identifying day boundaries based on End of Day and Start of Day operations,
and expanding reporting to support the use of those boundaries instead of
a fixed time of day (which is the same thing TouchBistro Cloud does). Customer
accounts are still only supported when used for payments, but none of the
pay in/out information (when done directly from the Customer Account admin
area) is reported, whereas it is included for Loyalty. We would also like to
continue building the ``changelog`` module, which is only half-working at the
moment. Menu items are supported but not menu categories, and much can be done
to improve that side of things.

Please submit a pull request for any ideas for code enhancements or fixes to
documentation etc.

