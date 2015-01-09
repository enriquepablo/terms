Interfacing with Terms
======================

Hey you Muscovite!
++++++++++++++++++

I see you are going through the Terms documentation,
and I would love to know your impressions about it.
If you read this, I encourage you to drop me a line
at enriquepablo@gmail.com, and tell me what you think,
ask me whatever is not clear in the docs, get support,
start some collaboration,
or anything at all.
Thanks for your interest anyway!

(End temp notice)
+++++++++++++++++

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

In the configuration file you can put as many
sections (e.g., ``[mykb]``) as you like,
one for each knowledge store.


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
