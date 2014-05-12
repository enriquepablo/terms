The formal theory behind Terms
==============================

Introduction
++++++++++++

Here I will develop a formal theory TT, that can be seen as the theoretical foundation ot Terms
(TT is meant to stand for Terms Theory).
TT has some similitudes with axiomatic set theory, even though its purpose and development are quite different (and much simpler).
The purpose of TT is more along the lines of knowledge representation and reasoning,
and would attempt to compete with things like description logics.
In any case, the origin of TT is in the study of the work of Frege, Russell, et al.,
and on its evolution towards axiomatic set theory, rather than on its evolution towards type theory,
so I will introduce TT by pointing out, first, its similitudes with set theory, and then its differences.
The particular formulation of set theory that I will use as reference is the system laid out by
A. A. Fraenkel, in his introduction to "Axiomatic Set Theory" by Paul Bernays (2nd ed. Amsterdam: North Holland Pub. Co., 1968),
and which he called system Z (for Zermelo, beacuse it was mainly based on Zermelo's 1908 system).
I rely on this system just for the clarity of its exposition,
rather than for any particular dependence on this formulation of set theory.

Fraenkel classified the axioms of system Z into 3 groups.
The first group, under the title "equality and extensionality",
had the purpose of establishing the interrelation between
the 3 basic predicates of the theory ("belongs to", "is subset of", and "equals").
In this group, Fraenkel put the axioms of extensionality and equality, and the definition of subset.

The 2nd group, which Fraenkel called "constructive axioms",
included the axioms of pairing, of sum-set, of power-set, and of subsets.
(The 3rd group included just the axiom of choice, and I won't go into it here.)
The purpose of this 2nd group of axioms is to guarantee the existence of certain sets.
In the words of Fraenkel:
"Constructive means that, certain things (one set, two sets, a set and a predicate) being given,
the axiom states the existence of a uniquely determined other set".

It is well known that the purpose of axiomatic set theory is to lay a foundation for all mathematics;
in the words of Fraenkel,
"setting up a comprehensive axiom system of set theory in which the axiomatic theories of other disciplines can be embedded".
The idea is to have a very rich universe of sets determined by a short list of axioms,
so that we can explore the internal structure of this universe
(by means of infering theorems from the basic axioms)
and extrapolate it to other disciplines.
There have more recently been other foundational efforts,
that have been more successful, by way of being simpler:
the intuitionistic type theory of Martin-Löf,
and later, still in development, homotopy type theory.
I won't go into these here, because TT is not meant to be a foundational effort.

If we just take the first group of axioms, we obtain a simple theory that is both consistent and complete.
It is also quite useless by itself.
We cannot infer any theorem, there is no set of which we can talk.
The theory limits itself to 3 axioms that do not say anything about anything,
the interpretation of which can simply be reduced to an empty universe.
Obviously, we need the "constructive" axioms to make something useful out of it.

However, there is another (trivial) way of using that first group of axioms,
to make what might be called formal classifications, or perhaps taxonomies.
In this sense, what we would do is to define individuals (sets) axiomatically,
ad hoc, to represent the classes and the objects we want to classify.
For example we might define an "animal" set, and a "mammal" subset of "animal",
and a "feline" subset of mammal; and we might define an individual "Felix the cat",
and state (axiomatically) that it belongs in "feline". From all this,
we would have, as theorems, that Felix is a mammal, and an animal,
thanks to the initial set of axioms.

To actually build such a formal taxonomy,
we could not have the same exact axioms as system Z,
due to the fact that universal extensionality
would preclude different empty individuals (ur-elements).
In any case, without constructive axioms,
it is trivial to prove the consistency and completeness of any such systems.
If, for simplicity, we assume a theory without equality,
we might use just a couple of axioms such as
(denoting the belongs relation by ``isa`` and the subset relation by ``is``):

1)  ``forall x, y, z: x is y & y is z -> x is z.``
2)  ``forall x, y, z: x isa y & y is z -> x isa z.``

This "formal taxonomy" theories have limited usefulness.
They allow us to represent, in a formal or mechanical system,
a certain knowledge that we previously had informally,
in the natural language.
However, in general, this falls short, and we additionally want
to say other things about the classified objects.
We usually want to represent other kind of knowledge appart from "taxonomic" knowledge.
In the natural language we represent this knowledge in the same way we
represent taxonomic knowledge, that is, using additional predicates:
conjugated verbs, modified by adverbs and objects.

Starting with Frege, and continuing with the logical positivists
(see for example Rudolf Carnap's "Introduction to symbolic logic and its applications"),
and later with the proponents of the semantic web, 
there have been numerous proposals for formal systems
catering for this need:
systems where, on top of a class system without constructive axioms,
there are additional techniques to express arbitrary knowledge.
At least to my knowledge, all these systems have something in common:
the arbitrary knowledge is expressed through formal predicates,
just the same as the taxonomic knowledge.

This presents a problem, because natural language predicates and formal predicates
are quite different things.
There is much more freedom in the use of natural language predicates:
we can quantify them and combine them in ways that are unthinkable
with the predicates of a formal system.
Therefore, when we take some natural language informal theory (some knowledge),
and try to express it in a formal system designed along those lines,
we very soon find trouble; and this trouble grows exponentially
with the complexity of the knowledge we are trying to express.

An example of this trouble might be seen in the OWL Full sublanguage of the semantic web,
where we can treat classes as individuals,
(which is equivalent to say that we can quantify over predicates,
since we can have anonymous classes defined over predicates),
but is undecidable, and cannot have dependable reasoning systems.

The theory TT
+++++++++++++

What I propose in TT is to use operations (rather than predicates)
to express "non-taxonomic" knowledge.

The individuals of TT are called "words", and they comply with the axioms (1) and (2) above.
Here, I will represent logical variables by ``x``, ``y``, ``z``, and ``w``,
and words by any other strings of lowercase alphanumeric characters.
We Now axiomatically add a first word, denoted by ``word``:

3)  ``forall x: x isa word.``

Now, we have an operator with which we can build triplets, denoted by ``[ ]``.
As operations, these triplets have word value, and so, can be related to other words
through ``is`` and ``isa``.
To introduce this operator, we first define a new word, ``verb``:

4)  ``verb is word.``
5)  ``forall x, y, z: y isa verb -> [ x y z ] isa y.``

So, in (4), we define ``verb`` as a word that can contain other words (it is a a subword of ``word``),
and in (5) we guarantee that each verb (each word that ``isa verb``)
"contains" all the triplets that can be formed with itself as middle term in the triplet.

Finally, we define one last word, ``fact``, that allows us to distinguish certain triplets (which we call facts):

6)  ``fact is word.``
7)  ``forall x, y, z: [ x y z ] isa fact -> y isa verb.``

So, in (6) we introduce ``fact`` as a word that can contain other words,
and with (7) we simply indicate that we can choose certain triplets and mark them as facts.
We can choose whatever triplets we want as facts, ad hoc.

The usage of this basic theory would be to extend it with additional ad hoc axioms,
to create what in other knowledge representation systems are called ontologies,
that represent particular pieces of "natural" knowledge.

Examples
++++++++

A trivial example.

English text (natural knowledge): There are people. John and Sue are people. To love is a verb. When a person loves another, the second loves the first. John loves Sue. Therefore Sue loves John::

  person is word.
  jonh isa person.
  sue isa person.

  love isa verb.

  forall x, y: [ x love y ] isa fact -> [ y love x ] isa fact.

  [ john love sue ] isa fact.

From this, we would have, as theorem, that ``[ sue love john ] isa fact.``

As said, this example is trivial, easily representable in any other system, such as OWL DL.
To show the possible power of TT, suppose that, rather than the previous simmetry rule for love, we say that::

  symmetry isa word.

  has-verb-property isa verb.

  forall x, y, z: [ y has-verb-property symmetry ] isa fact & [ x y z ] isa fact -> [ z y x ] isa fact.

  [ love has-verb-property symmetry ] isa fact.

  [ john love sue ] isa fact.

From this, we would also have as theorem that ``[ sue love john ] isa fact.``

You can in OWL DL define a symmetric relation: you have owl:SimmetricProperty.
But that is an integral part of the language.
Other DL may not have that kind of 'second order predicate'.
But, in TT we have just defined ``symmetry`` like any other word:
it is not an original part of the language.
We can then define reflexivity::

  reflexivity isa word.

  forall x, y: [ y has-verb-property reflexivity ] isa fact -> [ x y x ] isa fact.

and transitivity::

  transitivity isa word.

  forall x, y, z, w: [ y has-verb-property transitivity ] isa fact & [ x y z ] is a fact & [ z y w ] is a fact -> [ x y w ] isa fact.

Now we can define equivalence verbs::

  equivalence isa word.

  forall y: [ y has-verb-property equivalence ] isa fact -> [ y has-verb-property transitivity ] isa fact & [ y has-verb-property reflexivity ] isa fact &  [ y has-verb-property simmetry ] isa fact.


In the same sense, in the SW you cannot treat a class as an individual (unless you recurr to OWL Full)
but in TT, classes are individuals.

As a last example, we might say that Sue always gets whatever she wants::

  want isa verb.
  get isa verb.
  forall x: [ sue want x ] isa fact -> [ sue get x ] isa fact.

So, if we assert axiomatically that::

  [ sue want john ] isa fact.
  [ sue want love ] isa fact.
  [ sue want [ john love sue ] ] isa fact.
  [ sue want [ john want [ john love sue ] ] ] isa fact.

We would have as theorems that::

  [ sue get john ] isa fact.
  [ sue get love ] isa fact.
  [ sue get [ john love sue ] ] isa fact.
  [ sue get [ john want [ john love sue ] ] ] isa fact.

Semantics
+++++++++

The semantics of these formal theories could be found in the syntax of the natural language texts
that contain the knowledge we want to formalize,
disregarding the actual informal semantics of the natural language texts.
The universe of interpretation would be the set of words (names, nouns, and verbs)
that appear in the text.
The formal relations (``is``, ``isa``) in the theory are interpreted as hypothetical relations
established among words by the copular sentences in the text.
And the facts in the theory are interpreted in the non-copular sentences (or facts) in the text,
assuming that they are asserted as "it is a fact that <fact>"
(i.e., they are asserted as copular sentences,
since copular sentences are the only kind of sentence that can be interpreted as relations in these theories).
