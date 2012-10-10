The Terms knowledge store
=========================

Terms is a smart knowledge store.
It is used to store knowledge, that can later be queried.
It provides a declarative language with which to express the knowledge.
It is smart because this language can be used to express rules,
and these rules combine existing knowledge to produce new knowledge.

The Terms language
++++++++++++++++++

Here I will describe the Terms language.

To try the given examples, if you have installed Terms,
you have to type "terms" in a terminal,
and you will get a REPL where you can enter Terms constructs.
Follow the instuctions in the INSTALL.txt.

Words
-----

The main building block of Terms constructs are words.

To start with, there are a few predefined words:
``word``, ``verb``, ``noun``, ``number``, ``thing``, and ``exists``.

New words are defined relating them to existing words.

There are 2 relations that can be established among pairs of words.

These relations are formally similar to the set relations
"is an element of" and "is a subset of".

In English, we express the first relation as "is of type",
and in Terms it is expressed as::

    word1 is a word2.

So we would say that ``word1`` is of type ``word2``.
The second relation is expressed in English as "is subtype of",
and in Terms::

    a word1 is a word2.

So, we would say that ``word1`` is a subtype of ``word2``.
Among the predifined words, these relations are given::

    word is a word.
    verb is a word.
    a verb is a word.
    noun is a word.
    a noun is a word.
    thing is a noun.
    a thing is a word.
    exists is a verb.
    number is a word.

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

Verbs are special words in that they can have modifiers (or objects) when used to build facts.
These modifiers are words, and are labeled. To define a new verb, you provide
the types of words that can be objects for the verb in a fact,
associated with their label.
For example::

    loves is exists, subj a person, who a person.

That can be read as:
``loves`` is a word of type ``verb``, subtype of ``exists``,
and when used in facts it can take a subject of type ``person``
and an object labelled ``who`` of type ``person``.

Facts
-----

Facts are built with a verb and a number of objects.
They are given in parenthesis. For example, we might have a fact such as::

    (loves john, who sue).

The ``subj`` object is special: all verbs have it, and in sentences it is not
labelled with ``subj``, it just takes the place of the subject right after the verb.

Verbs inherit the object types of their ancestors. The primitive ``exists`` verb
only takes one object, ``subj``, of type ``word``, inherited by all the rest of the verbs.
So, if we define a verb::

    adores is loves.

It will have a ``who`` object of type ``person``. If ``adores`` had provided
a new object, it would have been added to the inherited ones.
A new verb can override an inherited object type to provide a subtype of the original
object type (like we have done above with ``subj``.)

Facts are not words,
but they are also individuals of the language,
"first class citizens",
and can be used wherever a word can be used.
Facts are of type ``exists``, and also of type <verb>,
were <verb> is the verb used to build the fact.

The objects in a fact can be of any type (a ``word``, a ``verb``, a ``noun``, a ``thing``,
a ``number``). In addition, they can also be facts (type ``exists``).
So, if we define a verb like::

    wants is exists, subj a person, what a exists.

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

We can use variables in rules. They are logical variables, used only to match words or facts,
and with a scope limited to the rule were they are used. We build variables by
capitalizing the name of the type of terms that it can match, and appending any number of
digits. So, for example, a variable ``Person1`` would match any person, such as
``sue`` or ``john``. With variables, we may build a rule like::

    (loves Person1, who Person2)
    ->
    (loves Person2, who Person1).

If we have this rule, and also that ``(loves john, who sue)``, the system will conclude
that ``(loves sue, who john)``.

Variables can match whole facts. For example, with the verbs we have defined, we could
build a rule such as::

    (wants john, what (Exists1))
    ->
    (Exists1).

With this, and ``(wants john, what (loves sue, who john)).``, the system would conclude
that ``(loves sue, who john)``.

Variables that match verbs or nouns have a special form, in that they are prefixed by
the name of a verb (or a noun), so that they match verbs that are subtypes of the given verb.
For example, with the terms we have from above, we might make a rule like::

    (LovesVerb1 john, who Person1)
    ->
    (loves Person1, who john).

In this case, ``LovesVerb1`` would match both ``loves`` and ``adores``, so both
``(loves john, who sue)`` and ``(adores john, who sue)`` would produce the conclusion
that ``(loves sue, who john)``.

Likewise for noun variables. In this case
an example might be ``PersonNoun1``. This variable would match ``person``,
and also ``man`` and ``woman``.

Finally, number variables are composed just with a capital letter and an integer, like
``N1``, ``P3``, or ``F122``.

Pythonic conditions
-------------------

In rules, we can add a section where we test conditions with Python, or where we produce
new variables out of existing ones. This is primarily provided to test arithmetic conditions
and to perform arithetic operations. This section is placed after the conditions,
between the symbols ``<-`` and ``->``. The results of the tests are placed in a
``condition`` python variable, and if it evaluates to ``False``, the rule is not fired.

To give an example, let's imagine some new terms::

    aged is exists, age a number.
    a bar is a thing.
    club-momentos is a bar.
    enters is exists, where a bar.

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


    [db]
    dbms = sqlite://
    dbname = :memory:
    [time]
    mode = normal

If it is activated, several things happen.

The first is that the system starts tracking the present time.
It has an integer register whose value represents the current time.
This register is updated each time we add new facts.
There are 3 possible values for the ``mode``
setting for time:
If the setting is ``none``, nothing is done with time.
If the setting is ``normal``, the current time of the system is incremented by 1 when it is updated.
If the setting is ``real``, the current time of the system
is updated with Python's ``import time; int(time.time())``.

The second thing that happens is that, rather than defining verbs extending ``exists``,
we use 2 new verbs, ``now`` and ``onwards``, both subtypes of ``exists``.
These new verbs have special number objects:
``now`` has an ``at_`` object, and ``onwards`` a ``since_`` and a ``till_`` objects.

The third is that the system starts keeping 2 different fatsets,
one for the present and one for the past.
All reasoning occurs in the present factset.
When we add a fact made with these verbs, the system automatically adds
to ``now`` an ``at_`` object and to ``onwards`` a ``since_`` object,
both with the value of its "present" register.
The ``till_`` object of ``onwards`` facts is left undefined.
We never explicitly set those objects.
When added, ``now`` facts go through the rule network, producing consecuences,
and then are added to the past factset;
``onwards`` facts go through the rules network and then are added
to the present factset.
Queries for ``now`` facts go to the past factset,
and those for ``onwards`` facts are done against the present.
We might say that the facts in the present factset are in
present continuous tense.

The fourth thing that happens when we activate the temporal logic
is that we can use a new predicate in the consecuances of our rules:
``finish``. We use it with an ``onwards`` fact: ``finish (<fact>).``
And when a rule with such a consecuence is activated,
it grabs the provided fact from the present factset,
adds to it a ``till_`` object with the present time as value,
removes it from the present factset,
and adds it to the past factset.
The system keeps track of the ancestry of facts obtained by reasoning,
and when a fact is finished, its descent (if otherwise unsupported)
is also finished.

**Miscelaneous technical notes.**

  * I have shown several different kinds of variables,
    for things, for verbs, for numbers, for facts.
    But the logic behind Terms is first order,
    there is only one kind of individuals,
    and the proliferation of kinds of variable
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
