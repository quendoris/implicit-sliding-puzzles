#!/usr/bin/env python3
"""Frozen constructive board profile for the million-side puzzle.

M9g0..M9g7 established a much simpler production path than the earlier
"arbitrary board -> physical category sort -> terminal target" construction:

    canonical --Q(seed)--> B
    B --Q(seed)^-1--> canonical

Q is a compact composition of legal U/D/L/R blank programs. Every primitive
also exposes exact forward/inverse positional maps, so B is exactly addressable
without materializing any of its 10^12 cells.

M9g7 measured the pure macroscopic wandering family at
160/192/224/256/320/384 rounds against calibrated finite-sample nulls. We
freeze 384 rounds here: it materially improves the residual dependence beyond
256/320 while retaining only a few thousand grammar nodes and O(rounds) random
access.

This module deliberately contains configuration, not another mixer variant.
Changing these constants is a new board format/profile decision and should be
re-audited statistically.
"""

from __future__ import annotations

from .seeded_legal_hamiltonian_board import SeededLegalHamiltonianBoard


CANONICAL_MILLION_SIDE=1_000_000
CANONICAL_MILLION_CELLS=CANONICAL_MILLION_SIDE*CANONICAL_MILLION_SIDE
CANONICAL_MILLION_ROUNDS=384
CANONICAL_MILLION_ANCHOR_MODE="wandering"
CANONICAL_PROFILE_NAME="M9g8-wandering-384"


def build_canonical_million_board(
    seed:int,
)->SeededLegalHamiltonianBoard:
    """Build the frozen exact-addressable trillion-cell board for seed."""
    return SeededLegalHamiltonianBoard(
        CANONICAL_MILLION_SIDE,
        seed,
        rounds=CANONICAL_MILLION_ROUNDS,
        anchor_mode=CANONICAL_MILLION_ANCHOR_MODE,
    )


def profile_manifest()->dict[str,object]:
    """Stable semantic configuration for external manifests/checkpoints."""
    return {
        "profile":CANONICAL_PROFILE_NAME,
        "side":CANONICAL_MILLION_SIDE,
        "cells":CANONICAL_MILLION_CELLS,
        "rounds":CANONICAL_MILLION_ROUNDS,
        "anchorMode":CANONICAL_MILLION_ANCHOR_MODE,
        "construction":"canonical --Q(seed)--> B",
        "solution":"Q(seed)^-1",
        "boardMaterializationRequired":False,
        "physicalMoveMaterializationRequired":False,
    }
