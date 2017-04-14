Contradictions in Gödel's First Incompleteness Theorem.
=======================================================

Intro
+++++

This refers to Kurt Gödel's
"On formally undecidable propositions of
principia mathematica and related systems".
The notation used here will be the same as
that used by Gödel in that paper.

In that work, Gödel starts with a description of the formal system P,
which, according to himself,
"is essentially the system obtained by superimposing
on the Peano axioms the logic of PM".

Then he goes on to define a map Phi,
which is an arithmetization of system P.
Phi is a one-to-one correspondence that assigns
a natural number, not only to every basic sign in P,
but also to every finite series of such signs.

One
+++

There are alternative arithmetizations of system P.
I will later delve on how many.

This is obvious from simply considering
a different order in the basic signs
when they are assigned numbers.
For example, if we assign the number 13 to "("
and the number 11 to ")",
we obtain a different Phi.

If we want Gödel's proof to be well founded,
it should obviously be independent of
which arithmetization is chosen to carry it out.
The procedure should be correct for any valid Phi chosen.
otherwise it would **not** apply to system P,
but to system P **and** some particular Phi.

To take care of this,
in Gödel's proof we must use a symbol for Phi
that represents abstractly any possible valid choice of Phi,
and that we can later substitute for a particular Phi
when we want to actually get to numbers.
This is so that we can show that substituting for any random Phi
will produce the same result,
and thus that the result is well founded.

The best way to do this is to add an index i to Phi,
coming from some set I with the same cardinality as
the set of all possible valid Phi's,
so we can establish a bijection among them - an index.
Thus Phi must become Phi^i.

Two
+++

Later on, Gödel proceeds to spell out Phi,
his Phi, which we might call Phi^0,
with his correspondence of signs and numbers
and his rules to combine them.

And then Gödel proceeds to define
a number of metamathematical concepts
about system P, that are
arithmetizable with Phi^0,
with 45 consecutive definitions,
culminating with the definition of provable formula.

Definition of provable formula means, in this context,
definition of a subset of the natural numbers,
so that each number in this set corresponds
biunivocally with a provable formula in P.

Let's now stop at his definition number (10):

  E(x) === R(11) * x * R(13)

Here Gödel defines "bracketing" of an expression x,
and this is the first time Gödel makes use of Phi^0,
since:

  Phi^0( '(' ) = 11

  Phi^0( ')' ) = 13

If we want to remain general, we should rather be doing:

   E^i(x) === R(Phi^i( '(' )) * x * R(Phi^i( ')' ))

Two little modifications are made in this definition.
First, we substitute 11 and 13 for Phi^i acting on "(" and ")".
11 and 13 would be the case if we instantiate the definition with Phi^0.

And second, E inherits an index i;
obviously, different Phi^i will define different  E^i.
And so do most definitions afterwards.

Since, for the moment, in the RHS of definitions from (10) onwards,
we are not encoding in Phi^i the index i,
which has sprouted on top of all defined symbols,
we cease to have an actual number there (in the RHS);
we now have an expresion that, given a particular Phi^i,
will produce a number.

So far, none of this means that any of Gödel's 45 deffinitions
are in any way inconsistent.

Three
+++++

There is something to be said of
the propositions Gödel labels as (3) and (4),
immediately after his 1-45 definitions.
With them, he establishes that, in his own words,
"every recursive relation [among natural numbers]
is definable in the [just arithmetized] system P",
i.e., with Phi^0.

So in the LHS of these two propositions
we have a relation among natural numbers,
and in the RHS we have a "number",
constructed from Phi^0 and his 45 definitions.
Between them, we have an arrow from LHS to RHS.
It is not clear to me from the text what
Gödel was meaning that arrow to be.
But it clearly contains an implicit Phi^0.

If we make it explicit and generalized, we must add indexes to
all the mathematical and metamathematical symbols he uses:
All Bew, Sb, r, Z, u1... must be generalized with an index i.

Then, if we instantiate with some particular Phi^i,
it must somehow be added in both sides:
in the RHS to reduce the given expression to an actual number,
and in the LHS to indicate that the arrow now goes from
the relation in the LHS **and** the particular Phi^i chosen,
to that actual number.

Obviously, if we want to produce valid statements about system P,
we must use indexes, otherwise the resulting numbers are
just talking about P and some chosen Phi^i, together.

Only after we have reached some statement about system P
that we want to corroborate,
should we instantiate some random Phi^i and see whether
it still holds, irrespective of any particularity of that map.

These considerations still do not introduce contradiction
in Gödel's reasoning.

Four
++++

So we need to keep the indexes in Gödel's proof.
And having indexes provides much trouble in (8.1).

In (8.1), Gödel introduces a trick that plays a central role in his proof.
He uses the arithmetization of a formula y to substitute free variables in that
same formula, thereby creating a self reference within the resulting expression.

However, given all previous considerations,
we must now have an index in y, we need y^i,
and so, it ceases to be a number.
But Z^i is some function that takes a natural number
and produces its representation in Phi^i.
It needs a number.

Therefore, to be able to do the trick of expressing
y^i with itself within itself,
we need to convert y^i to a number,
and so, we must also encode the index i with our 45 definitions.

Five
++++

But to encode the index,
we ultimately need to encode the actual Phi^i.
Such a thing is clear in the
(new) definition (10) of L^i provided above, in **two**.

Thus, if we want definitions 1-45 to serve for Gödel's proof,
we need an arithmetization of Phi^i itself -with itself.

This may seem simple enough, since, after all, the Phi^i are just maps,
But it leads to all sorts of problems.

Five one
--------

First of all, Phi^i deals with signs suchs as
parentheses and negation signs,
and it is difficult to see where will it
find them once it is arithmetized.
Above in **two** I have provided '(' to Phi^i,
for our revised definition (10);
but it is difficult to see how to encode '('
without using Phi^i,
so that we can feed it to the encoded Phi^i.

Five two
--------

Now, suppose that we can actually arithmetize any Phi^i with itself,
and that we pick some random Phi^i, let's call it Phi^0:
we can define Phi^0 with Phi^0,
and we can use that definition to further define 10-45.

But since Phi^0 is just a random arithmetization of system P,
if it suffices to arithmetize Phi^0,
then it must also suffice to define any other Phi^i equally well.
However, we can only use the arithmetization of Phi^0 to build defns 10-45.

This means that, as arithmetizations of system P,
the different Phi^i are not identical among them,
because each one treats differently the arithmetization of itself
from the arithmetization of other Phi^i.

So they are different as regards their representation of P,
and thus not very good representations;
they are inconsistent among them.

Exactly identical arithmetical statements,
such as definition (10) instatiated with some particular Phi^i,
acquire different meaning and truth value
when expressed in one or another Phi^i.

Among those statements, Gödel's theorem.

Five three
----------

The considerations in previous section **five two** also mean that
we cannot express, with some particular Phi^i,
definition (10) and onwards in their generality, for all Phi^i,
for they are clearly only valid for the Phi^i in which we are expressing them.

So definitions 10-45 are not possible in their generality
unless in the abstract context of a generalized Phi^i.

But we have already seen in setion **three** that we
need them generalized to be able to use them for Gödel'd proof.

Five four
---------

Further trouble comes from the consideration that
definitions 10-45 are actually an integral part of Phi^i,
and not just an use of it.
They further refine the set of selected numbers
to those that correspond, not just to random sequences of basic signs,
but to provable formulae.
And system P clearly is about provable formulae.

The trouble comes because now we have to express Phi^i
within Phi^i, not just with it,
and this means that it must contain itself, ad infinitum.

Five five
---------

A further argument that shows inconsistency in Gödel's theorem
comes from considering that if we are going to
somehow encode the index with Phi^i,
we should first consider what entropy must that index have, since
it will correspond to the size of the numbers that we will need to encode them.
And that entropy corresponds to the logarithm of the cardinality of I,
i.e., of the number of valid Phi^i.

To get an idea about the magnitude of this entropy, it may suffice
to think that variables have 2 degrees of freedom,
both with countably many choices.
Gödel very conveniently establishes a natural correspondence
between the indexes of the variables and the indexes of primes and of their consecutive
exponentiations, but in fact any correspondence between
both (indexes of vars, and indexes of primes and exponents) should do.
For example, we can clearly  have a Phi^i that maps the first variable of the first order
to the 1000th prime number exponentiated to the 29th  power.

This gives us all permutations of pairs of independent natural numbers,
and so, uncountably many choices for Phi^i;
so I must have at least the same cardinality as the real line.
Therefore y^i doesn't correspond to a natural number,
since it needs more entropy than a natural number can contain,
and cannot be fed into Z^i, terminating the proof.
