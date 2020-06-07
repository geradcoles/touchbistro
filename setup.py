"""
Set up the pdog-utils module.
"""
from setuptools import setup, find_packages


def readme():
    "Returns the contents of the README.rst file"
    with open("README.rst") as readmefile:
        return readmefile.read()


setup(
    name='touchbistro',
    version="0.1",
    description=(
        'Tools for reading and reporting from TouchBistro Sqlite3 database'),
    long_description=readme(),
    author='Prairie Dog Brewing CANADA Inc',
    author_email='gerad@prairiedogbrewing.ca',
    url='https://github.com/geradcoles/touchbistro',
    packages=find_packages(),
    install_requires=[],
    scripts=[
        'bin/payments',
        'bin/order',
	'bin/loyalty',
    ],
    test_suite="nose.collector",
)
