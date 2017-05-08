In his blog "Structural insight", John Shutt talks about Gödel's first
incompleteness theorem, stating it in terms of Turing machines.

To do so, he defines a Turing machine L, for Logic, that can take, as input, any
turing machine f plus an input/output pair appropriate for f, and will output
"confirm" in case f, given input i, produces
output o, and will not output "confirm" if such is not the case.
Since a Turing machine can only take as inputs sequences of symbols, it is
clear that to provide a Turing machine as input, we have to encode it in some
way that may be understood by the L machine.

After defining L, Shutt defines a table as follows. 
First, note that once we have a way to encode any Turing machine, we can also
use it to enumerate all possible Turing machines. So the table will have, as
rows, the enumeration of encoded Turing machines, and, as columns, an
enumeration of the possible inputs. And second, he uses the L machine to fill
in the cells of the table: in each cell, there is a "yes" if the machine in the
corresponding row outputs confirm when given the input in the corresponding
column, a "no" if L confirms that the given machine and input don't produce
confirm, and blank if L doesn't confirm ether.

Finally, Shutt proposes a Turing machine A, that contains both an enumeration
of encoded
Turing  machines and inputs, and a Turing machine L, that together determine a
table like described above. What A does, when given input i, is to go in the table
to the column for i, then go in the table to the diagonal cell corresponding to that
column, take the Turing machine in the corresponding row, use L to work out the
content of that diagonal cell, and finally output the contrary.

Now Gödel's theorem arises by considering what happens when A is given as input
the one that corresponds to its own diagonal cell in the table. In Shutt's
words:

<blockquote>
Since A is a Turing machine, it is the label on some row n of the table.  What is the content of table entry n,n?  Remember, the content of the table entry is what L actually confirms about the behavior of A on the nth input.  By construction, if the entry contains "no", then A outputs confirm, and the "no" is incorrect.  If the entry contains "yes", and the "yes" is correct, then A outputs confirm, and by construction it must have done so because the entry contains an incorrect "no" that caused A to behave this way.  Therefore, if L doesn't confirm anything that's false, this table entry must be blank.  But if we know the table entry is blank, then we know that, by failing to put a "no" there, L has failed to confirm something true, and is therefore incomplete.
</blockquote>

It seems obvious that there may be different ways to encode Turing machines,
and different L machines that take Turing machines differently encoded and analyse
them differently to determine their output. So let's use an index k to mark the
different L<sup>k</sup>. We will assume a
canonical 0 encoding, that can be produced and understood by humans, and
convene here that when we denote a Turing machine by some letter, we are
referring to its canonical encoding.

Now we define a new type of Turing machine, C<sup>k</sup> for compiler, that will take the
canonical encoding of any Turing machine, and output the same Turing machine
encoded for the L<sup>k</sup> machine.

Suppose now that we live in some kind of simulation, in an encoded world, and want to find out the
encoding in which we live -let's call it the w encoding,- and the L machine that "plays" us. In principle, it
seems clear that this should be impossible.

However, consider the following procedure. First, construct an enumeration of
encodings, or of L machines. The w encoding, and thus the L<sup>w</sup>
machine, should be anmong them. Then build an A machine for each encoding, and
run them.

In our w world, each time we run a Turing machine g, what we are effectively
doing is running L<sup>w</sup> ( C<sup>w</sup> ( g )).

So, should we be able to somehow distinguish between running L<sup>w</sup> ( C<sup>w</sup> ( A<sup>w</sup> ))
L<sup>w</sup> ( C<sup>w</sup> ( A<sup>k</sup> )) ?

I believe we might. In both cases, running A under L will reach an undecidable
state, and will produce inconsitent outputs. But if in one case the state is
reached earlier than in the other, we might be able to detect that.


So now the question becomes that of finding a path to undecidabity with Lw, C<sup>w</sup>, A<sup>w</sup>, and x, that is unavailable to Lw, C<sup>w</sup>, A<sup>k</sup> and z, and that is shorter than any available to the later.

So let's examine the following path.

We have Lw, C<sup>w</sup>, C<sup>w</sup>(A<sup>w</sup>), and x . We analyze C<sup>w</sup>(A<sup>w</sup>) and see that it contains Lw and an enumeration of C<sup>w</sup> encoded machines and inputs. We learn that we must use those enumerations to find out the next necessary operation, which is specified in the diagonal row to the x column. We find out what is in that row, and find C<sup>w</sup>(A<sup>w</sup>). We already have C<sup>w</sup>(A<sup>w</sup>), so we can recognize it. And now we learn that we have to output the contrary; but we already know that the contrary must be the same, we have already identified both machines as the same. Here we reach an undecidable state.

We have Lw, C<sup>w</sup>, C<sup>w</sup>(A<sup>k</sup>), and z . We analyze C<sup>w</sup>(A<sup>k</sup>) and see that it contains Lk and an enumeration of Ck encoded machines and inputs. We learn that we must use those enumerations to find out the next necessary operation, which is specified in the diagonal row to the z column. We find out what is in that row, and find Ck(A<sup>k</sup>). We already have C<sup>w</sup>(A<sup>k</sup>), **but** we cannot recognize it; as of now, we do not understand the k encoding. Now we have to use Lk to analyze A<sup>k</sup> and understand what to do. We are already past the state where we found undecidability in the previous case.

So at the moment it semms to me that there is a path, the possibility of leaking seems real. 
