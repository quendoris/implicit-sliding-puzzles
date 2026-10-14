# Constructive reachability and exact inverse

**Scope.** Let \(C\) be the canonical sliding-puzzle configuration on an even square board of side \(n\ge4\). The generator constructs a finite sequence of individually legal blank moves, denoted \(Q(s)\), parameterized by a nonnegative seed \(s\) and the frozen profile. Let \(B=Q(s)(C)\).

## Theorem 1: exact legal solution for constructed instances

If every move in \(Q(s)\) exchanges the blank with one orthogonally adjacent numbered tile, then \(B\) is physically reachable from \(C\). The sequence \(Q(s)^{-1}\), formed by reversing the move order and swapping \(U\leftrightarrow D\) and \(L\leftrightarrow R\), consists entirely of legal moves from \(B\) and restores exactly \(C\).

**Proof.** Each legal blank exchange is a bijection between consecutive configurations, whose inverse is the reverse blank move. Inverting a finite composition of bijections yields the reversed composition of their inverses. Induction over its length establishes legality of each reverse step and exact equality of the terminal configuration with \(C\). □

The result applies only to configurations produced by the generator; no minimal-length claim is made. Proof obligations for the implementation: the elementary straight blank runs and all generated Hamiltonian rectangle traversals must be individually legal and must keep the blank in the claimed position. Tests check these obligations by literal execution on small boards.

## Lemma 2: position queries

Let \(P_s\) be the permutation of **cell positions** induced by the legal program \(Q(s)\), carrying each initial cell's content to its final position. For a final cell \(p\), the numbered tile in that cell is

\[
\operatorname{valueAt}_s(p)=C(P_s^{-1}(p)).
\]

For a tile \(t\), whose canonical position is \(g(t)\),

\[
\operatorname{positionOf}_s(t)=P_s(g(t)).
\]

**Proof.** Each original cell's content is transported by exactly the same position permutation \(P_s\). The source cell of the content at final position \(p\) is \(P_s^{-1}(p)\). The second identity follows by applying \(P_s\) to the source of tile \(t\). □

The implementation evaluates primitive forward/inverse position maps without materializing all \(n^2\) cells. Time depends on the number of primitives and their evaluators, not on enumeration of the board.

## Lemma 3: indexed grammar

Each grammar node is \(\mathrm{Run}(d,k)\), \(\mathrm{PatternRepeat}(w,k)\), \(\mathrm{Sequence}(v_1,\ldots,v_m)\), \(\mathrm{Repeat}(v,k)\) or \(\mathrm{Empty}\). Store the (arbitrarily large) integer length of each node and prefix lengths of sequence children.

A move at index \(i\) can be obtained recursively: \(i\) indexes a run, is reduced modulo the pattern length, selects a child by cumulative prefix lengths, or is reduced modulo the repeated child's length. This terminates after at most the grammar depth. A sequence-child search costs \(O(\log m)\); all other node transitions are constant-time arithmetic operations, disregarding big-integer bit costs.

This supports a compact representation of an extremely long **particular generated program**. It does not constitute lossless compression of arbitrary permutations.

## Verification boundaries

Literal physical replay and independent source/destination checks on small boards test the full specified construction. Large-board tests verify exact algebraic identities for sampled cells and sampled move indices without materializing \(n^2\) cells or \(|Q|\) moves. The theorem is a mathematical statement about compositions of legal swaps; the finite tests detect implementation mistakes, but cannot replace the proof of each primitive's preconditions. Statistical uniformity and arbitrary-instance optimality are outside the theorem.
