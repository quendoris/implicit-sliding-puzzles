# Lemma: legal Hamiltonian rectangle cycle on an even-sided rectangle

Let `R=[r0,r1)×[c0,c1)` be an in-board rectangle with height `h>=2`,
width `w>=2`, and at least one even side. Suppose the blank starts at the
top-left corner `(r0,c0)`. Define `H_R` as follows.

## Row orientation (even height)

When `h` is even, visit the cells in the following *cyclic* order, measured
relative to the top-left corner:

1. All cells of row 0 from column 0 through column `w-1`.
2. For rows `1,...,h-1`, visit columns `1,...,w-1` in alternating directions:
   right-to-left on odd rows and left-to-right on even rows.
3. Return by the first column: `(h-1,0),(h-2,0),...,(1,0)`, then to `(0,0)`.

Every successive pair is orthogonally adjacent, including the last/first
pair. Every cell appears once before the final return to the anchor: the
visited sets in the three stages are disjoint and their cardinalities are
`w`, `(h-1)(w-1)`, and `h-1`, summing to `hw`.

The inter-row transition uses one vertical edge at the end of each alternating
row. Because `h` is even, the last serpentine row ends in column 1; the final
step to `(h-1,0)` is legal. All positions remain inside `R`.

## Column orientation (even width)

When `w` is even, transpose the row construction on the `w×h` rectangle
and swap row/column axes. Transposition preserves adjacency, coverage,
uniqueness and closure.

## Consequences

A closed blank walk visiting each of `hw` cells once swaps the blank with
the next occupant at every edge. It returns the blank to the anchor and
cyclically permutes the other `hw-1` occupants. Thus repeating a full
walk `k` times is physically legal, and its effect on numbered occupants
depends only on `k mod (hw-1)`.

The constructor's `HamiltonianRectangleCycle` represents exactly this
walk and its repeated grammar. The coordinate map is obtained by indexing
positions along the Hamiltonian ring and rotating the `hw-1` numbered
positions, while the blank stays at the anchor.

**Statement scope:** `h,w>=2`, at least one even side, rectangle in the
board, blank initially at anchor. The theorem does not cover arbitrary
rectangles whose blank is at a different point, and it does not imply
statistical uniformity or shortest solutions.

**Implementation checks:** `tests/test_rectangle_geometry.py` independently
executes each emitted elementary move and checks every forward/inverse
position for an exhaustive finite family of rectangle sizes, offsets,
orientations, and repetition counts. These tests support, but do not replace,
the preceding all-dimensions combinatorial argument.
