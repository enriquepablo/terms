Installation and usage
======================

Dependencies
++++++++++++

Python 3 (tested on 3.2, 3.3).

Python libraries (these should be pulled by ``easy_install``):
    * ply
    * sqlalchemy

Some RDBM system compatible with sqlalchemy (tested with postgreqsl and sqlite).

To run the tests, you need the ``nose`` framework.

Installation
++++++++++++

It is advisable to install in a virtualenv.

If you have setuptools installed in your python,
you can simply use ``easy_install``, from a command line::

    # easy_install Terms

Alternatively you can download `the tarball <http://pypi.python.org/packages/source/T/Terms/Terms-0.1.0a1.tar.gz>`_,
uncompress it,
``cd`` into the extracted directory,
and run ``python3 setup.py install``.

Interfacing
+++++++++++

Once installed, you should have a ``terms`` script,
that provides a REPL.

If you just type ``terms`` in the command line,
you will get a command line interpreter,
bound to an in-memory sqlite database.

If you want to make your Terms knowledge store persistent,
You have to write a small configuration file ``~/.terms.cfg``::

  [mykb]
  dbms = sqlite:////path/to/my/kbs
  dbname = mykb
  time = none

Then you must initialize the knowledge store::

  $ initterms mykb

And now you can start the REPL::

  $ terms mykb
  >>>

In the configuration file you can put as many
sections (e.g., ``[mykb]``) as you like,
one for each knowledge store.

To use PostgreSQL, you need the psycopg2 package,
that you can get with easy_install. Of course,
you need PostgreSQL and its header files for that.

The specified database must exist if you use
postgresql,
and the terms user (specified in the config file in the dbms URL)
must be able to create and drop tables and indexes.

    [testkb]
    dbms = postgresql://terms:terms@localhost
    dbname = testkb
    time = none

So, for example, once you are set, open the REPL::

    eperez@calandria$ initterms mykb
    eperez@calandria$ terms mykb
    >>> a person is a thing.
    >>> loves is exists, subj a person, who a person.
    >>> john is a person.
    >>> sue is a person.
    >>> (loves john, who sue).
    >>> (loves john, who sue)?
    true
    >>> (loves sue, who john)?
    false
    >>> quit
    eperez@calandria$ terms testing
    >>> (loves john, who sue)?
    true
