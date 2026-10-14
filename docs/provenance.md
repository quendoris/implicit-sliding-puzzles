# Source provenance — first extraction

The first implementation was extracted from the author's private research checkout `quendoris/uni` at commit `901933f0f7565b41f0a4f60bf56df5533dc9d65c`, from directory:

`02-optimization-methods/05-course-project/03-code/pilot/tools/`

| New module | Research source | Git source blob SHA |
|---|---|---|
| `src/implicit_sliding_puzzles/seeded_lazy_sampler.py` | `tools/seeded_lazy_sampler.py` | `de550666cac836938fd7721c8c5ea2bdd8822215` |
| `src/implicit_sliding_puzzles/recursive_plan_grammar.py` | `tools/recursive_plan_grammar.py` | `cfcbbd3ae0b5e3a3467d3e4e8a17c1feb6693041` |
| `src/implicit_sliding_puzzles/rectangle_cycle_macro.py` | `tools/rectangle_cycle_macro.py` | `4ae9dd8b38cd4b371861d028b9dde85dcabe447a` |
| `src/implicit_sliding_puzzles/hamiltonian_rectangle_cycle.py` | `tools/hamiltonian_rectangle_cycle.py` | `3b33f94122359b35a0c5090909d05b7426743be9` |
| `src/implicit_sliding_puzzles/seeded_legal_hamiltonian_board.py` | `tools/seeded_legal_hamiltonian_board.py` | `68c1876de39e14064484b87d4379ca59d6a82e74` |
| `src/implicit_sliding_puzzles/canonical_million_legal_board.py` | `tools/canonical_million_legal_board.py` | `225ac2821e47079003c5b0debd814043363df992` |
| `src/implicit_sliding_puzzles/million_solution_artifact.py` | `tools/million_solution_artifact.py` | `ff317c7eef66242982351c687af53b3f83c51958` |
| `src/implicit_sliding_puzzles/million_solution_query.py` | `tools/million_solution_query.py` | `ad8931b1f8a822326bf284ae7182e236030107ef` |

**Controlled refactor:** internal imports use a proper Python package; large Fmax-era dependencies `current_view_blankrun` and `indexed_current_view_plan` were replaced only for the `BlankRunTransform` case by `blank_run.py`. Its forward/inverse positional formulas preserve the source's cyclic blank-run mapping. New independent physical replay tests are stored under `tests/`.

The original research log metrics are **historical evidence**, not verified claims about this extraction until the tests pass.

Do not import the unreviewed source checkout wholesale or attach internal paths, credentials or private logs to releases.
