Installation and usage
======================

Installation
++++++++++++

I start with a clean basic debian 7.1 virtual machine,
only selecting the "standard system utilities" and
"ssh server" software during installataion.

Some additional software, first to compile python-3.3::

    # aptitude install vim sudo build-essential libreadline-dev zlib1g-dev libpng++-dev libjpeg-dev libfreetype6-dev libncurses-dev libbz2-dev libcrypto++-dev libssl-dev libdb-dev
    $ wget http://www.python.org/ftp/python/3.3.2/Python-3.3.2.tgz
    $ tar xzf Python-3.3.2.tgz
    $ cd Python-3.3.2
    $ ./configure
    $ make
    $ sudo make install

I install git, and an RDBMS::

    $ sudo aptitude install git postgresql postgresql-client  postgresql-server-dev-9.1

I allow method "trust" to all local connections for PostgreSQL, and create a "terms" user::

    $ sudo vim /etc/postgresql/9.1/main/pg_hba.conf
    $ sudo su - postgres
    $ psql
    postgres=# create role terms with superuser login;
    CREATE ROLE
    postgres=# \q
    $ logout

We get the buildout::

    $ git clone https://github.com/enriquepablo/terms-project.git

Make a python-3.3.2 virtualenv::

    $ cd terms-project
    $ pyvenv env
    $ . env/bin/activate
    $ python bootstrap.py
    $ bin/buildout

Now we initialize the knowledge store, and start the daemon::

    $ bin/initterms -c etc/terms.cfg

Now, you can start the REPL and play with it::

    $ bin/terms -c etc/terms.cfg
    >> a man is a thing.
    man
    >> quit
    $


XXX BELOW HERE IS OBSOLETE; I DON'T KNOW HOW MUCH XXX

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
you need PostgreSQL and its header files for that::

    $ easy_install Terms[PG]

The specified database must exist if you use
postgresql,
and the terms user (specified in the config file in the dbms URL)
must be able to create and drop tables and indexes::

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
