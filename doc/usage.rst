Interfacing with Terms
======================

Once you have installed Terms, you should have a ``terms`` script,
that provides a REPL. (If running a terms-basic docker container,
you are already in the REPL.)

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
  $ terms mykb
  >> (love john, who sue)?
  true

In the configuration file you can put as many
sections (e.g., ``[mykb]``) as you like,
one for each knowledge store.


Using the kbdaemon
++++++++++++++++++

Terms provides a daemon that listens on TCP port 1967.
If you are running a docker container from a terms-server image,
this is what you have got. If installed manually,
to use the daemon, you must add a"default" section to
the config file, with entries::

    [default]
    dbms = postgresql://terms:terms@localhost
    dbname = testkb
    time = normal

Now you can start the daemon::

    $ bin/kbdaemon start
    kbdaemon started
    $

And you can interface with it by making a TCP connection to port 1967 of the machine
and using the protocol described in the "protocol" section of this set of docs.
