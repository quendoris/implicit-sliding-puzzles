# Implicit Sliding Puzzles

Constructive generation of solvable sliding-puzzle instances with compact reversible move grammars and exact positional queries.

## Result A: constructive million-side boards

The frozen reference profile `M9g8-wandering-384` constructs an implicit board of **1,000,000 × 1,000,000** cells using legal blank moves. The program's structural inverse solves the **generated** instance. No globally optimal length or arbitrary-board solver is claimed.

Recorded verification of `M9g8`–`M9g10` (source checkout `901933f0f7565b41f0a4f60bf56df5533dc9d65c`):

| Measure | Recorded result |
| --- | ---: |
| Cells | 1,000,000,000,000 |
| Rounds | 384 |
| Grammar nodes | 5,379 |
| Physical moves (seed 10363137) | 96,288,361,077,053,954,149,714,072 |
| Serialized JSON artifact (same seed) | 678,347 bytes |
| Materialized cells / moves | 0 / 0 |

The reported figure for physical moves is the length **represented by** the grammar; this many moves have not been literally replayed on the million-side board.

## Reproduce

Python 3.11+ and the standard library suffice.

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m implicit_sliding_puzzles.million_solution_artifact build \
  --seed 10363137 --output million.solution.json
PYTHONPATH=src python3 -m implicit_sliding_puzzles.million_solution_artifact verify million.solution.json
PYTHONPATH=src python3 -m implicit_sliding_puzzles.million_solution_query move-at million.solution.json 0
```

These are newly extracted/refactored components; until CI and an independent local run have passed, the branch is **under review**, even though the older experiments had successful runs.

## Mathematical contract

See [constructive reachability and inverse](docs/proofs/constructive-reachability.md) and [source provenance](docs/provenance.md).

The JSON contains a SHA-256 integrity digest, not a signature or proof of authorship.

## Publications

Articles and immutable PDFs are managed outside this source repository. An article must link to an immutable release/tag and evidence manifest.

## License status

This is a public review branch. Licensing is not granted merely by public visibility. Code and documentation license files will be chosen explicitly before a stable release.
