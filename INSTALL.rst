Installation and usage
======================

Installation with setuptools on a virtualenv
++++++++++++++++++++++++++++++++++++++++++++

You don't need to use pythonbrew,
but you must make sure you are using python 3.3.0 or above::

    $ pythonbrew use 3.3.0

Make a virtualenv, and install setuptools::

    $ pyvenv test-terms
    $ cd test-terms/
    $ . bin/activate
    $ wget https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py -O - | python

Install Terms (in this case, with PostgreSQL support)::

    $ easy_install Terms[PG]

Installation with buildout on a clean debian machine
++++++++++++++++++++++++++++++++++++++++++++++++++++

I use this to develop Terms.

Start with a clean basic debian 7.1 virtual machine,
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

Install git, and an RDBMS::

    $ sudo aptitude install git postgresql postgresql-client  postgresql-server-dev-9.1

Allow method "trust" to all local connections for PostgreSQL, and create a "terms" user::

    $ sudo vim /etc/postgresql/9.1/main/pg_hba.conf
    $ sudo su - postgres
    $ psql
    postgres=# create role terms with superuser login;
    CREATE ROLE
    postgres=# \q
    $ logout

Get the buildout::

    $ git clone https://github.com/enriquepablo/terms-project.git

Make a python-3.3.2 virtualenv::

    $ cd terms-project
    $ pyvenv env
    $ . env/bin/activate

Edit the configuration file and run the buildout
(if you ever change the configuration file,
you must re-run the buildout)::

    $ vim config.cfg
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


Interfacing with Terms
++++++++++++++++++++++

Once installed, you should have a ``terms`` script,
that provides a REPL.

If you just type ``terms`` in the command line,
you will get a command line interpreter,
bound to an in-memory sqlite database.

If you want to make your Terms knowledge store persistent,
you must edit the configuration file,
and add a section for your knowledge store.
If you have installed Terms with easy_install,
you must create this configuration file in ``~/.terms.cfg``::

  [mykb]
  dbms = sqlite:////path/to/my/kbs
  dbname = mykb
  time = none

Then you must initialize the knowledge store::

  $ initterms mykb

And now you can start the REPL::

  $ terms mykb
  >>

In the configuration file you can put as many
sections (e.g., ``[mykb]``) as you like,
one for each knowledge store.

Using PostgreSQL
++++++++++++++++

To use PostgreSQL, you need the psycopg2 package,
that you can get with easy_install. Of course,
you need PostgreSQL and its header files for that::

    $ sudo aptitude install postgresql postgresql-client  postgresql-server-dev-9.1
    $ easy_install Terms[PG]

The database specified in the configuration file must exist if you use
postgresql,
and the user (specified in the config file in the dbms URL)
must be able to create and drop tables and indexes.
You would have a config file like::

    [mykb]
    dbms = postgresql://terms:terms@localhost
    dbname = testkb
    time = normal

So, for example, once you are set, open the REPL::

    eperez@calandria$ initterms mykb
    eperez@calandria$ terms mykb
    >> a person is a thing.
    >> to love is to exist, subj a person, who a person.
    >> john is a person.
    >> sue is a person.
    >> (love john, who sue).
    >> (love john, who sue)?
    true
    >> (love sue, who john)?
    false
    >> quit
    eperez@calandria$ terms testing
    >> (love john, who sue)?
    true

Using the kbdaemon
++++++++++++++++++

Terms provides a daemon that listens on TCP port 1967.
To use the daemon, you must put your config in a section of the config file named "default"::

    [default]
    dbms = postgresql://terms:terms@localhost
    dbname = testkb
    time = normal

Now you can start the daemon::

    $ bin/kbdaemon start
    kbdaemon started
    $

And you can interface with it by making a TCP connection to port 1967 of the machine
and using the protocol described at the end of the README.rst.
