The Terms language
==================

Here I will describe the Terms language. 

To try the examples given below, if you have installed Terms,
you have to type "terms" in a terminal,
and you will get a REPL where you can enter Terms constructs.
To install Terms, follow the instuctions :doc:`here <install>`.

More examples `can be found here <https://github.com/enriquepablo/terms-server/tree/master/terms/server/app/ontology>`.

Words
+++++

The main building block of Terms constructs are words.
They are the only data type there is in the Terms language.
There are 2 basic operation that involve words:
composing them to produce facts,
and matching variables in the rules.

To start with, there are a few predefined words:
``word``, ``verb``, ``noun``, ``number``, ``thing``, and ``exist``.

New words are defined relating them to existing words.

There are 2 relations that can be established among pairs of words.

As we shall see below,
these relations are formally similar to the set relations
"is an element of" and "is a subset of".

In English, we express the first relation as "is of type",
and in Terms it is expressed as::

    word1 is a word2.

So we would say that ``word1`` is of type ``word2``,
defining ``word1`` in terms of ``word2``
(so ``word2`` must have been defined before, or be predefined).

The second relation is expressed in English as "is subtype of",
and in Terms::

    a word1 is a word2.

So, we would say that ``word1`` is a subtype of ``word2``,
also defining ``word1`` in terms of ``word2``.
Among the predefined words, these relations are given::

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
    ...

In general, identifiers for words must have the form of
a string that starts with a lower case alphabetic character,
followed by any number of aphabetic character, dashes or
underscores, optionally ending in any number of digits.
The pattern for this is ``r'[a-z][a-z-_]*\d*'``.
Additionally, words of type ``thing`` can be any string
quoted in double quotes, with pattern ``r'"(""|[^"])*"'``.


Facts
+++++

With words, we can build facts.
Facts consist, at least, of a verb and a subject,
and are given in parentheses.
The subject can be a word of any type,
but the verb must be of type ``verb``.
The primitive verb is ``exist``,
so an example of a fact could be::

    (exist sue).

In addition to a subject and a verb,
a fact can have any number of objects.
Like the subject, objects can be words of any type.
The types of words that can be objects for a given verb
are determined in the definition of the verb.
Therefore, definitions of verbs are special,
and do not follow the general syntax shown above.

Since a fact using a verb can have less objects
than are determined in the definition of the verb,
the objects are labelled.
The definition of a verb ``<verb1>`` in terms of ``<verb2>`` takes the following form::

    to <verb1> is to <verb2>, subj a <word1>, <label1> a <word2>, <label2> a <word3>...

An example might be::

    to love is to exist, subj a person, who a person.

This defines a verb ``love``, that is subtype of ``exist``,
and that forms facts with a subject of type ``person``
and an object labelled ``who`` of type ``person``.
With it, we may build a fact such as::

    (love john, who sue).

The ``subj`` (subject) is just a special object: all verbs have it
(it is determined in the definition of ``exist``),
and in facts it is not labelled with ``subj``,
it just takes the place of the subject right after the verb.

Verbs inherit the object types of their ancestors.
So, if we define a verb::

    to adore is to love.

It will have a ``who`` (and a ``subj``) object of type ``person``. If ``adore`` had provided
a new object, it would have been added to the inherited ones.
A new verb can override an inherited object type to provide a subtype of the original
object type
(like we have done above with ``subj``)

Facts are words,
"first class citizens",
and can be used wherever a word can be used.
Facts are words of type ``exist``, and also of type <verb>,
were <verb> is the verb used to build the fact;
and, in the case where a fact is asserted,
we can imagine a word ``fact`` so that asserting a fact ``(love john, who sue)``
is actually syntactic sugar for
``(love john, who sue) is a fact.``
This is, however, hidden in the implementation,
and in Terms we only allow one-to-one typing,
so that a word can only be defined in relation to just one type.

Since facts are words, if we define a verb like::

    to want is to exist, subj a person, what a exist.

We can then build facts like::

    (want john, what (love sue, who john)).

And indeed::

    (want john, what (want sue, what (love sue, who john))).

Rules
+++++

We can build rules, that function producing new facts out of existing (or newly added) ones.
A rule has 2 sets of facts, the conditions (given first) and the consecuences. The facts in each set of
facts are separated by semicolons (conjunctions), and the symbol ``->`` (implication) separates the conditions
from the consecuences.
A simple rule might be::

    (love john, who sue)
    ->
    (love sue, who john).

The facts in the knowledge base are matched with the conditions of rules,
and when all the conditions of a rule are matched by coherent facts,
the consecuences are added to the knowledge base. The required coherence
among matching facts concerns the variables in the conditions.

We can use variables in rules. They are logical variables, used only to match words,
and with a scope limited to the rule were they are used. We build variables by
capitalizing the name of the type of words that it can match, and appending any number of
digits. So, for example, a variable ``Person1`` would match any person, such as
``sue`` or ``john``. With variables, we may build a rule like::

    (love Person1, who Person2)
    ->
    (love Person2, who Person1).

If we have this rule, and also that ``(love john, who sue)``, the system will conclude
that ``(love sue, who john)``.

Variables can match whole facts. For example, with the verbs we have defined, we could
build a rule such as::

    (want john, what Exists1)
    ->
    (Exists1).

With this, and ``(want john, what (love sue, who john)).``, the system would conclude
that ``(love sue, who john)``.

Variables that match verbs (or nouns) have a special form, in that they are prefixed by
the name of a verb (or a noun), so that they match verbs (or nouns) that are subtypes of the prefix verb (or noun).
For example, with the words we have from above, we might make a rule like::

    (LoveVerb1 john, who Person1)
    ->
    (LoveVerb1 Person1, who john).

In this case, ``LoveVerb1`` would match both ``love`` and ``adore``, so both
``(love john, who sue)`` and ``(adore john, who sue)`` would produce the conclusion
that ``(love sue, who john)`` or ``(adore sue, who john)``.

For a more elaborate example we can define a new verb::

    to be-allowed is to exist, subj a person, to a verb.

and a rule::

    (want Person1, what (LoveVerb1 Person1, who Person2));
    (be-allowed Person1, to LoveVerb1)
    ->
    (LoveVerb1 Person1, who Person2).

Then, ``(be-allowed john, to adore)`` would allow him to adore but not to love.

We can use word variables, e.g. ``Word1``, that will match any word or fact.

In conditions, we may want to match a whole fact, and at the same time match some of
its component words. To do this, we prepend the fact with the name
of the fact variable, separated with a colon. With this, the above rule would become::

    (want Person1, what Love1:(LoveVerb1 Person1, who Person2));
    (be-allowed Person1, to LoveVerb1)
    ->
    (Love1).


Integers
++++++++

Integers are of type ``number``.
We don't define numbers, we just use them.
Any sequence of characters that can be cast as an integer type in Python
are numbers in Terms, e.g.: ``1``.

Number variables are composed just with a capital letter and an integer, like
``N1``, ``P3``, or ``F122``.

Pythonic conditions
+++++++++++++++++++

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
    (want Person1, what (enters Person1, where Bar1))
    <-
    condition = N1 >= 18
    ->
    (enters Person1, where Bar1).

If we have that::

    (aged sue, age 17).
    (aged john, age 19).
    (want sue, what (enters sue, where club-momentos)).
    (want john, what (enters john, where club-momentos)).

The system will (only) conclude that ``(enters john, where club-momentos)``.

Negation
++++++++

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
with a single string argument, a Terms fact (possibly with variables) as a string,
that will return the number of facts in the db matching the given one.
We can use this to test for the absence of any given fact
in the knowledge base, and thus have negation by failure.

Some care must be taken with the ``count`` function.
If a fact is entered that might match a pythonic ``count`` condition in a rule,
it will never by itself trigger the rule.
Rules are activated by facts matching normal conditions;
and pythonic conditions can only allow or abort
those activations.
In other words, when a fact is added,
it is tested against all normal conditions in all rules,
and if it activates any rule, the pythonic conditions are tested.

Time
++++

In the monotonic classical logic we have depicted so far,
it is very simple to represent physical time:
you only need to add a ``time`` object of type ``number``
to any temporal verb.
However, to represent the present time, the now,
i.e., a changing distinguished individual instant of time,
this logic is not enough.
We need to use some non-monotonic tricks for that,
that are implemented in Terms as a kind of temporal logic.
This temporal logic can be activated in the settings file
(see the :doc:`install docs <install>` for more on the settings file)::


    [mykb]
    dbms = postgresql://terms:terms@localhost
    dbname = mykb
    time = normal
    instant_duration = 60

Time can only be activated if you are using the daemon
to talk to Terms (rather than the REPL, see the :doc:`interfacing docs <usage>`)
If it is activated, several things happen.

The first is that the system starts tracking the present time:
It has an integer register whose value represents the current time.
This register is updated every ``config['instant_duration']`` seconds.
There are 3 possible values for the ``time``
setting:
If the setting is ``none``, nothing is done with time.
If the setting is ``normal``, the current time of the system is incremented by 1 when it is updated.
If the setting is ``real``, the current time of the system
is updated with Python's ``import time; int(time.time())``.

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
Each time the time is updated, all ``occur`` facts are removed from the present
and added to the past factset, and thus stop producing consecuences.
Queries for ``occur`` facts go to the past factset if we specify an ``at_`` object in the query,
and to the present if an ``at_`` object is not provided.
The same thing in queries goes for ``endure`` facts, substituting ``at_`` with ``since_``.
We might say that the ``endure`` facts in the present factset (with an undefined ``till_`` object) are in
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
any previous present facts with the same subject and verb are ``finish`` ed.

A further verb, ``happen``, derived from ``occur``, has the singularity that,
when a fact is added as a consecuence of other facts, and is built
with a verb derived from ``happen``, is fed through the network connection back to the
user adding the facts that are producing consecuences.


Querying
++++++++

Queries are sets of facts separated by semicolons,
with or without variables.
If the query contains no variables, the answer will be ``true``
for presence of the asked facts or ``false`` for their absence.
To find out whether a fact is negated we must query its negation.

If we include variables in the query,
we will obtain all the variable substitutions
that would produce a ``true`` query,
in the form of a json list of mappings of strings.

However, we can not add special constraints,
like we can in rules with pythonic conditions.
