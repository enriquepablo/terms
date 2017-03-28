Installation
============

Docker
++++++

You can use Docker to run Terms, see
`terms-docker <https://github.com/enriquepablo/terms-docker>`_.
This is the easiest and recommended way to test Terms.

Installation with setuptools on a virtualenv
++++++++++++++++++++++++++++++++++++++++++++

You must make sure you are using python 3.3.0 or above.
Make a virtualenv, and install setuptools::

    $ pyvenv test-terms
    $ cd test-terms/
    $ . bin/activate
    $ wget https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py -O - | python

Install Terms (in this case, with PostgreSQL support, in which case you need
the devel package for postgresql-server installed in your system)::

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

To use this configuration, you must have created a testkb database in PostgreSQL,
and it must be configured such that a user terms with password terms
has permissions to insert and create tables in testkb.
