# Implicit Sliding Puzzles

Constructive generation of solvable sliding puzzles using compact, reversible move programs and exact positional queries.

## Scope

The first result constructs a family of **reachable** sliding-puzzle configurations by applying a legal sequence of blank moves to the canonical board. Its inverse is a complete, deterministic solution for the **constructed instances**. Compact grammars make the board and solution addressable without materializing all cells or all moves.

This is not a claim to optimally solve arbitrary sliding-puzzle permutations. Work on global F-max optimization is maintained separately.

## First verification target

- Board: `1,000,000 × 1,000,000` (one trillion cells)
- Frozen research profile: `M9g8-wandering-384`
- Three recorded JSON solution artifacts: 678,347–678,399 bytes
- Exact addressable move program: physical lengths around `10^26` steps
- Validation: literal small-board replay, sparse large-board queries, serialization/integrity and bounded move-window tests

These are **recorded research results**, not fresh CI measurements of this repository. Executable reproduction, independent verification and provenance will be added as separately reviewable units before any release is declared.

## Repository organization

The initial implementation, mathematical definitions, source provenance, experimental fixtures and independent checks are developed in review branches. Revisions become public releases only after reproducibility and license reviews.

**Publication status:** working public research repository. No final release has been certified.

## Publications

Immutable PDFs and their checksums will be distributed separately, linked to exact source commits and release identifiers.

## Attribution and licensing

Original research is attributed to its authors. Source and documentation licensing will be explicitly established before a public release; until then, publication of the repository does not itself grant an open-source reuse license.
