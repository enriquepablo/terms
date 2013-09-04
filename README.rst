The Terms knowledge store
=========================

Terms is a knowledge store.
It provides a declarative language to express and query that knowledge.
The main claim to usefulness that Terms has
lies in the Terms language:
It is purported to be very powerful,
and very close to the natural languages.

Terms is licensed under the GPLv3, and is hosted at
`github <https://github.com/enriquepablo/terms>`_.

The Terms language
++++++++++++++++++

Here I will describe the Terms language.

Terms is a declarative logic language. 

With it you can:
 * define new words (nouns, verbs, and names);
 * build facts out of your defined words;
 * build rules that combine given facts to produce new facts;
 * perform complex queries.


It is similar to other logic languages,
such as prolog, or CLIPS
(it is nearer to CLIPS in that it is forward chaining, based on a RETE network),
but it is more powerful, because all defined items (or terms)
have the same category. What do I mean with the same category?
Well, in Terms, you build sentences, or facts,
that have a verb and any number of objects,
and these objects can be any kind of term:
Names, verbs, or nouns, or even other facts.
In contrast, to build facts in prolog or in CLIPS,
you use as verbs a special kind of item, a predicate,
that cannot be treated as an object;
or, you cannot use other facts as objects.
In Terms, a rule can have a logical variable
that ranges over any fact or term,
something that is unthinkable in (idiomatic) prolog or CLIPS.

However, Terms is based on a first order theory,
interpreted in a finite universe,
so it might be implemented in any of those languages;
that's why I specified "idiomatic".

To try the examples given below, if you have installed Terms,
you have to type "terms" in a terminal,
and you will get a REPL where you can enter Terms constructs.
To install Terms, follow the instuctions in the INSTALL.rst.

More examples can be found in the
`github repository <https://github.com/enriquepablo/terms/tree/master/terms/core/examples>`_.

Words
-----

The main building block of Terms constructs are words.

To start with, there are a few predefined words:
``word``, ``verb``, ``noun``, ``number``, ``thing``, and ``exist``.

New words are defined relating them to existing words.

There are 2 relations that can be established among pairs of words.

As we shall see below,
these relations are formally similar to the set theory relations
"is an element of" and "is a subset of".

In English, we express the first relation as "is of type",
and in Terms it is expressed as::

    word1 is a word2.

So we would say that ``word1`` is of type ``word2``,
defining ``word1`` in terms of ``word2``.
The second relation is expressed in English as "is subtype of",
and in Terms::

    a word1 is a word2.

So, we would say that ``word1`` is a subtype of ``word2``,
also defining ``word1`` in terms of ``word2``.
Among the predifined words, these relations are given::

    word is a word.
    verb is a word.
    a verb is a word.
    noun is a word.
    a noun is a word.
    thing is a noun.
    a thing is a word.
    exist is a verb.
    a exist is a word.
    number is a word.
    a number is a word.

To define a new word, you put it in relation to an existing word. For example::

    a person is a thing.
    a man is a person.
    a woman is a person.
    john is a man.
    sue is a woman.

These relations have consecuences, given by 2 implicit rules::

    A is a B; a B is a C -> A is a C.
    a A is a B; a B is a C -> a A is a C.

Therefore, from all the above, we have, for example, that::

    thing is a word.
    person is a word.
    person is a noun.
    john is a word.
    a man is a thing.
    john is a thing.
    sue is a person.

With these words, we can build facts.
A fact consists of a verb and any number of (labelled) objects.

Verbs are special words in that they take modifiers (or objects) when used to build facts.
These modifiers are words, and are labeled. To define a new verb,
you provide first an ancestor verb (or a series of ancestor verbs separated by colons),
and then the types of words that can be modifiers for the verb in a fact,
associated with their labels.
For example::

    to loves is to exist, subj a person, who a person.

That can be read as:
``loves`` is a word of type ``verb``, subtype of ``exist``,
and when used in facts it can take a subject of type ``person``
and an object labelled ``who`` also of type ``person``.

The primitive verb is ``exist``,
that just defines a ``subj`` object of type ``thing``.
There are more predefined verbs,
the use of which we shall see when we explain the treatment of time in Terms.

Facts
-----

Facts are built with a verb and a number of objects.
They are given in parenthesis. For example, we might have a fact such as::

    (loves john, who sue).

The ``subj`` object is special: all verbs have it, and in sentences it is not
labelled with ``subj``, it just takes the place of the subject right after the verb.

Verbs inherit the object types of their ancestors. The primitive ``exist`` verb
only takes one object, ``subj``, of type ``word``, inherited by all the rest of the verbs.
So, if we define a verb::

    to adores is to loves.

It will have a ``who`` object of type ``person``. If ``adores`` had provided
a new object, it would have been added to the inherited ones.
A new verb can override an inherited object type to provide a subtype of the original
object type (like we have done above with ``subj``.)

Facts are words,
"first class citizens",
and can be used wherever a word can be used.
Facts are words of type ``exist``, and also of type <verb>,
were <verb> is the verb used to build the fact.
So our facts are actually synctactic sugar for
``(loves john, who sue) is a loves.``

The objects in a fact can be of any type (a ``word``, a ``verb``, a ``noun``, a ``thing``,
a ``number``). In addition, they can also be facts (type ``exist``).
So, if we define a verb like::

    to wants is to exist, subj a person, what a exist.

We can then build facts like::

    (wants john, what (loves sue, who john)).

And indeed::

    (wants john, what (wants sue, what (loves sue, who john))).

Rules
-----

We can build rules, that function producing new facts out of existing (or newly added) ones.
A rule has 2 sets of facts, the conditions and the consecuences. The facts in each set of
facts are separated by semicolons, and the symbol ``->`` separates the conditions
from the consecuences.
A simple rule might be::

    (loves john, who sue)
    ->
    (loves sue, who john).

The facts in the knowledge base are matched with the conditions of rules,
and when all the conditions of a rule are matched by coherent facts,
the consecuences are added to the knowledge base. The required coherence
among matching facts concerns the variables in the conditions.

We can use variables in rules. They are logical variables, used only to match words,
and with a scope limited to the rule were they are used. We build variables by
capitalizing the name of the type of words that it can match, and appending any number of
digits. So, for example, a variable ``Person1`` would match any person, such as
``sue`` or ``john``. With variables, we may build a rule like::

    (loves Person1, who Person2)
    ->
    (loves Person2, who Person1).

If we have this rule, and also that ``(loves john, who sue)``, the system will conclude
that ``(loves sue, who john)``.

Variables can match whole facts. For example, with the verbs we have defined, we could
build a rule such as::

    (wants john, what Exists1)
    ->
    (Exists1).

With this, and ``(wants john, what (loves sue, who john)).``, the system would conclude
that ``(loves sue, who john)``.

Variables that match verbs (or nouns) have a special form, in that they are prefixed by
the name of a verb (or a noun), so that they match verbs (or nouns) that are subtypes of the given verb (or noun).
For example, with the words we have from above, we might make a rule like::

    (LovesVerb1 john, who Person1)
    ->
    (loves Person1, who john).

In this case, ``LovesVerb1`` would match both ``loves`` and ``adores``, so both
``(loves john, who sue)`` and ``(adores john, who sue)`` would produce the conclusion
that ``(loves sue, who john)``.

For a more elaborate example we can define a new verb::

    to allowed is to exist, subj a person, to a verb.

and a rule::

    (wants Person1, what (LovesVerb1 Person1, who Person2));
    (allowed Person1, to LovesVerb1)
    ->
    (LovesVerb1 Person1, who Person2).

Then, ``(allowed john, to adores)`` would allow him to adore but not to love.

We can use word variables, e.g. ``Word1``, that will match any word or fact.

In conditions, we may want to match a whole fact, and at the same time match some of
its component words. To do this, we prepend the fact with the name
of the fact variable, separated with a colon. With this, the above rule would become::

    (wants Person1, what Loves1:(LovesVerb1 Person1, who Person2));
    (allowed Person1, to LovesVerb1)
    ->
    (Loves1).


Numbers
-------

Numbers are of type ``number``.
We don't define numbers, we just use them.
Any sequence of characters that can be cast as a number type in Python
are numbers in Terms, e.g.: ``1``, ``-1e12``, ``2-3j``, ``10.009`` are numbers.

Number variables are composed just with a capital letter and an integer, like
``N1``, ``P3``, or ``F122``.

Pythonic conditions
-------------------

In rules, we can add a section where we test conditions with Python, or where we produce
new variables out of existing ones. This is primarily provided to test arithmetic conditions
and to perform arithetic operations. This section is placed after the conditions,
between the symbols ``<-`` and ``->``. The results of the tests are placed in a
``condition`` python variable, and if it evaluates to ``False``, the rule is not fired.

To give an example, let's imagine some new terms::

    to aged is to exist, age a number.
    a bar is a thing.
    club-momentos is a bar.
    to enters is to exist, where a bar.

Now, we can build a rule such as::

    (aged Person1, age N1);
    (wants Person1, what (enters Person1, where Bar1))
    <-
    condition = N1 >= 18
    ->
    (enters Person1, where Bar1).

If we have that::

    (aged sue, age 17).
    (aged john, age 19).
    (wants sue, what (enters sue, where club-momentos)).
    (wants john, what (enters john, where club-momentos)).

The system will (only) conclude that ``(enters john, where club-momentos)``.

Negation
--------

We can use 2 kinds of negation in Terms, classical negation and
negation by failure.

**Classical negation**

Any fact can be negated by prepending ``!`` to its verb::

    (!aged sue, age 17).

A negated fact is the same as a non-negated one.
Only a negated fact can match a negated fact,
and they can be asserted or used in rules.
The only special thing about negation is that
the system will not allow a fact and its negation
in the same knowledge base: it will warn of a contradiction
and will reject the offending fact.

**Negation by failure**

In pythonic conditions, we can use a function ``runtime.count``
with a single string argument, a Terms fact (possibly with variables),
that will return the number of facts in the db matching the given one.
We can use this to test for the absence of any given fact
in the knowledge base, and thus have negation by failure.

Some care must be taken with the ``count`` function.
If a fact is entered that might match a pythonic ``count`` condition,
it will never by itself trigger any rule.
Rules are activated by facts matching normal conditions;
and pythonic conditions can only allow or abort
those activations.
In other words, when a fact is added,
it is tested against all normal conditions in all rules,
and if it activates any rule, the pythonic conditions are tested.
An example of this behaviour can be seen
`here <https://github.com/enriquepablo/terms/blob/master/terms/core/tests/person_loves.test>`_.
If you examine the ontology in the previous link,
you will see that it is obviously wrong;
that's the reason I say that care must be taken.
Counting happens in time,
and it is not advisable to use it without activating time.

Time
----

In the monotonic classical logic we have depicted so far,
it is very simple to represent physical time:
you only need to add a ``time`` object of type number
to any temporal verb.
However, to represent the present time,
i.e., a changing distinguished instant of time,
this logic is not enough.
We need to use some non-monotonic tricks for that,
that are implemented in Terms as a kind of temporal logic.
This temporal logic can be activated in the settings file::


    [mykb]
    dbms = postgresql://terms:terms@localhost
    dbname = mykb
    time = normal
    instant_duration = 60

If it is activated, several things happen.

The first is that the system starts tracking the present time.
It has an integer register whose value represents the current time.
This register is updated every ``instant_duration`` seconds.
There are 3 possible values for the ``mode``
setting for time:
If the setting is ``none``, nothing is done with time.
If the setting is ``normal``, the current time of the system is incremented by 1 when it is updated.
If the setting is ``real``, the current time of the system
is updated with Python's ``import time; int(time.monotonic())``.

The second thing that happens is that, rather than defining verbs extending ``exist``,
we use 2 new verbs, ``occur`` and ``endure``, both subtypes of ``exist``.
These new verbs have special ``number`` objects:
``occur`` has an ``at_`` object, and ``endure`` a ``since_`` and a ``till_`` objects.

The third is that the system starts keeping 2 different factsets,
one for the present and one for the past.
All reasoning occurs in the present factset.
When we add a fact made with these verbs, the system automatically adds
to ``occur`` an ``at_`` object and to ``endure`` a ``since_`` object,
both with the value of its "present" register.
The ``till_`` object of ``endure`` facts is left undefined.
We never explicitly set those objects.
When added, ``occur`` facts go through the rule network, producing consecuences,
and then are added to the present factset;
``endure`` facts go through the rules network and then are also added
to the present factset.
Each time the time is updated, all ``occur`` facts are removed from the present
and added to the past factset, and thus stop producing consecuences.
Queries for ``occur`` facts go to the past factset if we specify an ``at_`` object in the query,
and to the present if an ``at_`` object is not provided.
The same goes for ``endure`` facts, substituting ``at_`` with ``since_``.
We might say that the ``endure`` facts in the present factset are in
present continuous tense.

The fourth thing that happens when we activate the temporal logic
is that we can use a new predicate in the consecuances of our rules:
``finish``. This verb is defined like this::

    to finish is to exist, subj a thing, what a exist.

And when a rule with such a consecuence is activated,
it grabs the provided ``what`` fact from the present factset,
adds a ``till_`` object to it with the present time as value,
removes it from the present factset,
and adds it to the past factset.

There is also the temporal verb ``exclusive-endure``, subverb of ``endure``.
The peculiarity of ``exclusive-endure`` is that whenever a fact with
such verb is added to the knowledge base,
any previous present facts with the same subject and verb are ``finish``ed.

A further verb, ``happen``, derived from ``occur``, has the singularity that,
when a fact is added as a consecuence of other facts, and is built
with a verb derived from ``happen``, is fed through the pipeline back to the
user adding the facts that are producing consecuences.


Querying
--------

Right now the query language of Terms is a bit limited.
Queries are facts, with or without variables.
If the query contains no variables, the answer will be ``true``
for presence of the asked facts or ``false`` for their absence.
To find out whether a fact is negated we must query its negation.

If we include variables in the query,
we will obtain all the variable substitutions
that would produce a ``true`` query,
in the form of a json list of mappings of strings.

Several facts can be anded in a query,
separating them with semicolons.

However, we can not add special constraints,
like we can in rules with pythonic conditions.


**Miscelaneous technical notes.**

  * I have shown several different kinds of variables,
    for things, for verbs, for numbers, for facts.
    But the logic behind Terms is first order,
    there is only one kind of individuals,
    and the proliferation of kinds of variables
    is just syntactic sugar.
    ``Person1`` would be equivalent to something like
    "for all x, x is a person and x...".
    ``LovesVerb1`` would be equivalent to something like
    "for all x, a x is a loves and x...".

 *  The design of the system is such that
    both adding new facts (with their consecuences)
    and querying for facts should be independent of
    the size of the knowledge base.
    The only place where we depend on the size of the data
    is in arithmetic conditions,
    since at present number objects are not indexed as such.

 * The Python section of the rules is ``exec``ed
   with a dict with the ``condition`` variable in locals
   and an empty dict as globals. We might add whatever we
   like as globals; for example, numpy.


The Terms Protocol
++++++++++++++++++

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


