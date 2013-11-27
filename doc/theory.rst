The formal theory behind Terms
==============================


Here I will develop a first order theory T
that can be seen as the theoretical foundation of Terms.
It will be simpler than Terms,
and in particular,
all verbs will be binary,
so facts will be basically triples.

The signature of T consists of a finite (and small) set of constants,
denoted with strings of lowercase characters;
a ternary operation denoted by a pair of parentheses;
and 2 binary relations denoted ``C`` and ``E``.

As variables we will use ``x``, ``y``, and ``z``.

Two axioms of transitivity give form to ``E`` and ``C``
(with all variables universally quantified in their
outernmost possible scope)::

  x C y & y C z -> x C z

  x E y & y C z -> x E z

The form thus given to ``C`` and ``E``
makes them similar to the set-theoretic predicates,
"belongs to" and "is subset of".

In addition there are a few distinguished constants.
First there is ``word``, so that for all ``x`` ::

  x E word

Then we have ``verb``, of which we can both say that ::

  verb E word
  verb C word

In English, we call the constants "words".
If 2 words are related by ``E``, we say that one is of type of the other,
and if 2 words are related by ``C``, we say that one is subtype of the other.
Constants that are of type ``verb``, we call "verbs".
Finally, we call "facts" to the triples ``(a b c)``.

We can now use our ternary operation to
make facts::

  x E verb -> (y x z) E x

This ensures the existence of any possible fact.

We now introduce a final distinguished constant, ``fact``.
We use it to distinguish certain facts;
those we want asserted.

  fact E word
  fact C word

  (x y z) E fact -> y E verb

Interpretation
--------------

T is interpreted in the natural language, in English.
The domain of interpretation is the set of nouns and (non-copulative) verbs
of the English language,
and the relations in T are interpreted as English copular sentences.

In addition, the facts of T that are of type ``fact``,
are interpreted as English facts (non-copular sentences).

Advantage over other logical AI systems
---------------------------------------

We can indiscriminatelly quantify over the constructs used to
stand for names, nouns, verbs, and facts.
