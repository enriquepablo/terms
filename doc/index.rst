The Terms Project
=================

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
   contact

Introduction
++++++++++++

Terms is a `production rule system <https://en.wikipedia.org/wiki/Production_system>`_
that is used to build `expert <https://en.wikipedia.org/wiki/Expert_system>`_
and `knowledge representation and resoning <https://en.wikipedia.org/wiki/Knowledge_representation>`_ systems.
Its inference capabilities are based on a `Rete Network <https://en.wikipedia.org/wiki/Rete_algorithm>`_.
The data structures for both the Rete network (RN) and the knowledge bases (KBs) it manipulates
are implemented in a relational database, so it is appropriate to build long term
knowledge stores to which new facts can be added incrementally.
The facts and rules that give content to the KBs and RN are expressed in the
Terms language (from now on, just "Terms" where there is no ambiguity).

Terms is a declarative language that is based on a very simple first order theory,
interpreted in a finite domain. It is thus a fairly simple language,
that has many similarities with other logic languages,
such as Prolog or CLIPS,
but in a sense is more expressive,
as I will try to show.
The main building block of Terms facts are what we call words,
of which there are several types: verbs, nouns, names, and more;
even facts are themselves words.
To compose a fact, we need a verb and a number of argument terms, or objects;
and any type of word can act as an object.
In contrast, to build facts for example in Prolog,
you use as verbs a special kind of item, a predicate,
that cannot be treated as an argument term.

Next I show a session with a Terms REPL
using an empty KB and RN, to give a taste of what it looks like.
First I define a few words, then add a rule to the network,
provide some facts to the KB, and make some queries against it.
Prededined symbols, including words, are presented in bold typeface.

.. parsed-literal::

  >> she **is a thing**.
  >> **a** food **is a thing**.
  >> this-banana **is a** food.
  >> **to** eat **is to exist,** what **a** food.
  >> **to** want **is to exist,** what **a** word.
  >> **to** get **is to exist,** what **a** word.
  >> (want she, what Word1)
  \.. ->
  \.. (get she, what Word1).
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
