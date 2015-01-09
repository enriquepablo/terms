The Terms Protocol
==================

Hey you Muscovite friend!
+++++++++++++++++++++++++

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

Once you have a knowledge store in place and a kb daemon running::

    $ mkdir -p var/log
    $ mkdir -p var/run
    $ bin/kbdaemon start

You communicate with it through a TCP socket (e.g. telnet),
with a communication protocol that I shall describe here.

A message from a client to the daemon, in this protocol, is a series of
utf8 coded byte strings terminated by the string ``'FINISH-TERMS'``.

The daemon joins these strings and, depending on a header,
makes one of a few things.
A header is an string of lower case alfabetic characters,
separated from the rest of the message by a colon.

* I there is no header, the message is assumed to be
  a series of constructs in the Terms language,
  and fed to the compiler.
  Depending on the type of constructs, the response can be different:

  * If the construct is a query, the response is a json string
    followed by the string ``'END'``;
  
  * If the constructs are definitions, facts and/or rules,
    the response consists on the series of facts that derive as
    consecuences of the entered constructs, that are constructed
    with a verb that ``is to happen``, terminated by the string ``'END'``.

* If there is a ``lexicon:`` header, the response is a json string
  followed by the string ``'END'``. The contents of the json depend
  on a second header:
  
  * ``get-subwords`` returns a list of word names that are subword
    of the word whose name is given after the header.
  
  * ``get-words:`` returns a list of word names that are
    of the type of the word whose name is given after the header.
  
  * ``get-verb:`` return a representation of the objects that the verb
    named after the header has. For each object, there is a list with
    3 items:
    
    * A string with the name of the label;
    
    * A string with the name of the type of the object;
    
    * A boolean that signals that the object must be a fact in itself.

* If there is a ``compiler:`` header:
  
  * If there is an ``exec_globals:`` header, the string that follows
    is assumed to be an exec_global, and fed to the knowledge store as such.
  
  * If there is a ``terms:`` header, what follows are assumed to be
    Terms constructs, and we go back to the first bullet point in this series.
