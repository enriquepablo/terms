Terms
=====

Terms is a `production rule system <https://en.wikipedia.org/wiki/Production_system>`_
that is used to build `expert <https://en.wikipedia.org/wiki/Expert_system>`_
and `knowledge representation and resoning <https://en.wikipedia.org/wiki/Knowledge_representation>`_ systems.
Its inference capabilities are based on a `Rete Network <https://en.wikipedia.org/wiki/Rete_algorithm>`_.
The data structures for both the Rete network (RN) and the knowledge bases (KBs) it manipulates
are implemented in a relational database, so Terms is most appropriate to build long term
knowledge stores to which new facts can be added incrementally.
The facts and rules that give content to the KBs and RN are expressed in the
Terms language (from now on, just "Terms" where there is no ambiguity).

Terms is a logic programming language,
that has similarities with other logic programming languages,
such as Prolog:
it is declarative, and knowledge is expressed as facts and rules,
that are made up of atomic and compound terms.
However, Terms is, in a sense, more expressive than Prolog,
as I will try to show next.
The basic building block of Terms constructs are what we call words,
of which there are several types: verbs, nouns, names, numbers, and a few more;
even facts are themselves words.
To compose a fact, we need a verb and a number of arguments, or objects;
and any type of word can act as an object,
including facts, or the verbs used to build facts.
In contrast, to build facts in Prolog,
you use as verbs a special kind of item, a predicate,
that cannot be treated as an argument term.
The variables used in Terms rules
range -in principle- over the set of all words,
including facts and the verbs used to compose facts,
whereas variables in Prolog cannot range over predicates,
unless you consider higher order extensions to Prolog.

The formal basis for Terms is a :doc:`first order theory <theory>`
and, as such, might easily be implemented in Prolog (based on first order logic),
so I am not claiming that Terms is more generally powerful than Prolog.
What I claim is that it is idiomatically more appropriate
to formally represent the kind of knowledge that
people manage with the natural languages.

Next I show a session with a Terms REPL
using an empty KB and RN, to give a taste of what it looks like.
Prededined symbols, including words but excluding punctuation,
are presented in bold typeface.


First we define some words. We define a noun ``food``,
2 names ``she`` and ``this-banana``, and 3 verbs ``eat``, ``want`` and ``get``:

.. parsed-literal::

  >> she **is a thing**.
  >> **a** food **is a thing**.
  >> this-banana **is a** food.
  >> **to** eat **is to exist,** what **a** food.
  >> **to** want **is to exist,** what **a** word.
  >> **to** get **is to exist,** what **a** word.

Next we provide a rule:

.. parsed-literal::

  >> (want she, what Word1)
  \.. ->
  \.. (get she, what Word1).

Anf finally we enter some facts and make some simple queries:

.. parsed-literal::

  >> (want she, what this-banana).
  >> (get she, what this-banana)?
  true
  >> (get she, what eat)?
  false
  >> (want she, what eat).
  >> (get she, what eat)?
  true
  >> (want she, what food).
  >> (get she, what food)?
  true
  >> (get she, what (eat she, what this-banana))?
  false
  >> (want she, what (eat she, what this-banana)).
  >> (get she, what (eat she, what this-banana))?
  true
  >> (eat she, what this-banana)?
  false
  >> (eat she, what this-banana).
  >> (eat she, what this-banana)?
  true

Contents
++++++++

.. toctree::
   :maxdepth: 1

   Introduction <index>
   language
   install
   usage
   protocol
   theory
