TouchBistro Database Python Library
===================================

For reading a TouchBistro Sqlite3 database and creating reports that are not
currently present through the cloud.

IMPORTANT: Always run this tool against a copy of the TouchBistro Sqlite3
database.

Bad things could happen if this report runs queries that lock the
active database while TouchBistro is using it, possibly destroying your
restaurant point of sale.

Installation
------------

Install this program like you would any typical Python module from git::

    git clone git@github.com:geradcoles/touchbistro.git
    cd touchbistro
    pip install -r requirements.txt
    python setup.py install # or develop if you plan on hacking code

Order Details
-------------

The order details library and shell script are very useful for digging into
the details of orders at a depth not visible in TouchBistro, itself. Item
modifiers and discounts are visible in a receipt-like format, and a much more
detailed JSON format outputs both high and low-level fields about the order,
order line items, modifiers, discounts and payments, including cash,
electronic, customer account, and Loyalty account payments. Gratuities and
partial/multiple payments are supported, as well as refunds.

Here's an example of a command-line invocation of the ``order`` commamnd set
to the default, receipt-like view of an order::

    order fetch Restaurant.sql 30031

        ORDER DETAILS FOR ORDER #30031

    Order Date/Time:     	2020-04-22 09:34:13 PM
    Table Name: None	Party Name: Joe
    Bill Number: 40080	Order Type: takeout
    Server Name: Nancy S

    -----------------------------------------------

    Adult Chicken Tenders                  $15.00
    - $7.50: Staff: Joe Discount
                        Item Subtotal:     $7.50

    Popplers                               $7.00
    - $3.50: Staff: Joe Discount
                        Item Subtotal:     $3.50

    Grizzly Paw Black Cherry               $4.00
    - $4.00: Shift Joe Discount
                        Item Subtotal:     $0.00


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
modifiers and discounts. Next, we have the order subtotal and tax amount
(tax is not working yet), followed by the order total amount.

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

Get a summary of paid orders for a specified time period like this::

    payments /path/to/Restaurant.sql --from=2020-03-26 --to=2020-04-23

Add the ``--csv`` flag if you plan to use Excel to view or manipulate the data::

    payments /path/to/Restaurant.sql \
        --from=2020-03-26 \
        --to=2020-04-23 \
        --csv > output.csv


