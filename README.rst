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

Paid Order Summary
------------------

Get a summary of paid orders for a specified time period like this::

    payments /path/to/Restaurant.sql --from=2020-03-26 --to=2020-04-23

Add the ``--csv`` flag if you plan to use Excel to view or manipulate the data::

    payments /path/to/Restaurant.sql \
        --from=2020-03-26 \
        --to=2020-04-23 \
        --csv > output.csv


