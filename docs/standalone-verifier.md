# Standalone artifact verifier

The script `tools/verify_artifact.py` requires only Python 3.11+ and the standard library. It never imports the board generator, grammar decoder or serializer.

It independently checks:
- canonical JSON artifact SHA-256 and an optional pinned expected digest;
- format and million-side profile metadata;
- recursive grammar structure, direction alphabet, counts and calculated big-integer length;
- grammar node count, depth, and digest;
- exact move lookup at specified indices.

Run:

```sh
PYTHONPATH=src python -m implicit_sliding_puzzles.million_solution_artifact build \
  --seed 10363137 --output million.solution.json
python tools/verify_artifact.py million.solution.json \
  --expected-sha256 a8c80310b66d5cc5a8638485a611c4630e09edaf105e4df1ed7807b6fca1dd85 \
  --indices 0,1,48144180538526977074857036
```

**Boundary:** the independent program verifies the serialized move *grammar*, not that every grammar move is physically legal on the implicit trillion-cell board. That stronger claim rests on the construction theorem and primitive proofs plus small-board replay. A stronger external independent verifier for the positional transformation algebra remains a separate proof obligation.
