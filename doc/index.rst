Terms
=====

Introduction
++++++++++++

Terms is a `production rule system <https://en.wikipedia.org/wiki/Production_system>`_
that is used to build `expert <https://en.wikipedia.org/wiki/Expert_system>`_
and `knowledge representation and resoning <https://en.wikipedia.org/wiki/Knowledge_representation>`_ systems.
Its inference capabilities are based on a `Rete Network <https://en.wikipedia.org/wiki/Rete_algorithm>`_.
The data structures for both the Rete network (RN) and the knowledge bases (KBs) it manipulates
are implemented in a relational database, so Terms is most appropriate to build long term
persistent knowledge stores to which new facts can be added incrementally.
The facts and rules that give content to the KBs and RN are expressed in the
Terms language (from now on, just "Terms" where there is no ambiguity).

Terms is a logic programming language,
that has similarities with other logic programming languages,
such as Prolog:
it is declarative, and knowledge is expressed as facts and rules,
that are made up of atomic and compound terms.
The main difference with Prolog, from a logical point of view,
is that where Prolog is based on first order logic,
Terms is based on :doc:`a first order theory </theory>`.
A program in Prolog might be said to correspond
with a first order theory,
so Terms might be implemented in Prolog.
The purported advantage of Terms is that
it is idiomatically more appropriate to express the kind of knowledge that
people express with the natural languages.

Next I show a session with a Terms REPL
using an empty KB and RN, to give a taste of what it looks like.
Predefined symbols, including words but excluding punctuation,
are presented in bold typeface.


First we define some words. We define a noun ``food``,
2 names ``she`` and ``this-banana``, and 3 verbs ``eat``, ``want`` and ``get``:

.. parsed-literal::

  >> she **is a thing**.
  >> **a** food **is a thing**.
  >> this-banana **is a** food.
  >> **to** eat **is to exist,** what **a** food.
  >> **to** want **is to exist,** what **a word**.
  >> **to** get **is to exist,** what **a word**.

Next we provide a rule:

.. parsed-literal::

  >> (want she, what **Word1**)
  \.. ->
  \.. (get she, what **Word1**).

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

   Home <index>
   language
   theory
   install
   usage
   protocol
   contact
