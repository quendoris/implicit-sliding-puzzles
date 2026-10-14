#!/usr/bin/env python3
"""Compact Hamiltonian blank cycle over every cell of an even-sided rectangle.

If rectangle height is even, use the canonical row-serpentine cycle:

    top row left -> right,
    then rows 1..h-1 across columns 1..w-1 in alternating directions,
    bottom-left,
    then first column bottom -> top back to the anchor.

The blank starts and ends at top-left and visits every cell exactly once before
returning.  For odd height / even width, use the transpose construction.

One full cycle therefore rotates ALL h*w-1 numbered occupants by one position
in the Hamiltonian numbered-ring order.  Repeat(loop,k) rotates by k with:

* exact legal UDLR;
* O(1) structural grammar size;
* O(1) coord <-> Hamiltonian-index arithmetic;
* O(1) forward/inverse positional queries independent of h*w.

This strictly generalizes the 2xN/Nx2 strip rotation primitive and is the
candidate physical block-rotation engine for M9f3c2+.
"""

from __future__ import annotations

from dataclasses import dataclass

from .rectangle_cycle_macro import (
    Rectangle,
)
from .recursive_plan_grammar import (
    PlanNode,
    repeat,
    run,
    sequence,
)


def _row_serpentine_loop(
    *,
    height:int,
    width:int,
)->PlanNode:
    if height<2 or width<2 or height%2:
        raise ValueError(
            "row-serpentine Hamiltonian loop requires even height >=2"
        )

    pair=sequence(
        run(
            "D",
            1,
        ),
        run(
            "L",
            width-2,
        ),
        run(
            "D",
            1,
        ),
        run(
            "R",
            width-2,
        ),
    )
    pair_count=(
        height-2
    )//2

    return sequence(
        run(
            "R",
            width-1,
        ),
        repeat(
            pair,
            pair_count,
        ),
        run(
            "D",
            1,
        ),
        run(
            "L",
            width-1,
        ),
        run(
            "U",
            height-1,
        ),
    )


def _column_serpentine_loop(
    *,
    height:int,
    width:int,
)->PlanNode:
    """Transpose of _row_serpentine_loop(width,height)."""
    if height<2 or width<2 or width%2:
        raise ValueError(
            "column-serpentine Hamiltonian loop requires even width >=2"
        )

    pair=sequence(
        run(
            "R",
            1,
        ),
        run(
            "U",
            height-2,
        ),
        run(
            "R",
            1,
        ),
        run(
            "D",
            height-2,
        ),
    )
    pair_count=(
        width-2
    )//2

    return sequence(
        run(
            "D",
            height-1,
        ),
        repeat(
            pair,
            pair_count,
        ),
        run(
            "R",
            1,
        ),
        run(
            "U",
            height-1,
        ),
        run(
            "L",
            width-1,
        ),
    )


@dataclass(frozen=True)
class HamiltonianRectangleCycle:
    rect:Rectangle
    count:int
    preferred_orientation:str|None=None

    def __post_init__(self)->None:
        if self.count<0:
            raise ValueError(
                "Hamiltonian cycle count cannot be negative"
            )
        if (
            self.rect.height%2
            and self.rect.width%2
        ):
            raise ValueError(
                "Hamiltonian rectangle cycle requires at least one even side"
            )
        if self.preferred_orientation not in (
            None,
            "row",
            "column",
        ):
            raise ValueError(
                "preferred_orientation must be row, column, or None"
            )
        if (
            self.preferred_orientation=="row"
            and self.rect.height%2
        ):
            raise ValueError(
                "row orientation requires even rectangle height"
            )
        if (
            self.preferred_orientation=="column"
            and self.rect.width%2
        ):
            raise ValueError(
                "column orientation requires even rectangle width"
            )

    @property
    def orientation(self)->str:
        if self.preferred_orientation is not None:
            return self.preferred_orientation
        return (
            "row"
            if self.rect.height%2==0
            else "column"
        )

    @property
    def cells(self)->int:
        return (
            self.rect.height
            *self.rect.width
        )

    @property
    def numbered_ring_cells(self)->int:
        return self.cells-1

    @property
    def effective_count(self)->int:
        return (
            self.count
            %self.numbered_ring_cells
        )

    @property
    def loop_plan(self)->PlanNode:
        if self.orientation=="row":
            return _row_serpentine_loop(
                height=self.rect.height,
                width=self.rect.width,
            )
        return _column_serpentine_loop(
            height=self.rect.height,
            width=self.rect.width,
        )

    @property
    def plan(self)->PlanNode:
        return repeat(
            self.loop_plan,
            self.effective_count,
        )

    @property
    def loop_physical_length(self)->int:
        return self.cells

    @property
    def physical_length(self)->int:
        return (
            self.loop_physical_length
            *self.effective_count
        )

    @staticmethod
    def _row_index(
        row:int,
        col:int,
        height:int,
        width:int,
    )->int:
        if not (
            0<=row<height
            and 0<=col<width
        ):
            raise IndexError(
                (
                    row,
                    col,
                )
            )

        if row==0:
            return col

        if col>0:
            base=(
                width
                +(row-1)*(width-1)
            )
            if row&1:
                offset=(
                    width-1-col
                )
            else:
                offset=(
                    col-1
                )
            return base+offset

        # First-column return leg starts at bottom-left and climbs upward.
        base=(
            width
            +(height-1)*(width-1)
        )
        return (
            base
            +(height-1-row)
        )

    @staticmethod
    def _row_coord(
        index:int,
        height:int,
        width:int,
    )->tuple[int,int]:
        cells=height*width
        if not 0<=index<cells:
            raise IndexError(
                index
            )

        if index<width:
            return (
                0,
                index,
            )

        nonzero_columns=(
            (height-1)
            *(width-1)
        )
        q=index-width
        if q<nonzero_columns:
            row=(
                1
                +q//(
                    width-1
                )
            )
            offset=q%(
                width-1
            )
            col=(
                width-1-offset
                if row&1
                else 1+offset
            )
            return (
                row,
                col,
            )

        q-=nonzero_columns
        return (
            height-1-q,
            0,
        )

    def cycle_index(
        self,
        rc:tuple[int,int],
    )->int:
        row=rc[0]-self.rect.r0
        col=rc[1]-self.rect.c0
        if self.orientation=="row":
            return self._row_index(
                row,
                col,
                self.rect.height,
                self.rect.width,
            )
        # Transpose local coordinates.  Width is even, therefore the
        # transposed height is even and uses the same closed form.
        return self._row_index(
            col,
            row,
            self.rect.width,
            self.rect.height,
        )

    def coord_at_cycle_index(
        self,
        index:int,
    )->tuple[int,int]:
        if self.orientation=="row":
            row,col=self._row_coord(
                index,
                self.rect.height,
                self.rect.width,
            )
        else:
            transposed_row,transposed_col=self._row_coord(
                index,
                self.rect.width,
                self.rect.height,
            )
            row,col=(
                transposed_col,
                transposed_row,
            )
        return (
            self.rect.r0+row,
            self.rect.c0+col,
        )

    def numbered_ring_index(
        self,
        rc:tuple[int,int],
    )->int|None:
        if rc==self.rect.anchor:
            return None
        try:
            index=self.cycle_index(
                rc
            )
        except IndexError:
            return None
        if index==0:
            return None
        return index-1

    def numbered_ring_coord(
        self,
        index:int,
    )->tuple[int,int]:
        if not 0<=index<self.numbered_ring_cells:
            raise IndexError(
                index
            )
        return self.coord_at_cycle_index(
            index+1
        )

    def forward_ring_index(
        self,
        index:int,
    )->int:
        if not 0<=index<self.numbered_ring_cells:
            raise IndexError(
                index
            )
        return (
            index-self.effective_count
        )%self.numbered_ring_cells

    def inverse_ring_index(
        self,
        index:int,
    )->int:
        if not 0<=index<self.numbered_ring_cells:
            raise IndexError(
                index
            )
        return (
            index+self.effective_count
        )%self.numbered_ring_cells

    def forward(
        self,
        rc:tuple[int,int],
    )->tuple[int,int]:
        if rc==self.rect.anchor:
            return rc

        row,col=rc
        if not (
            self.rect.r0<=row<self.rect.r1
            and self.rect.c0<=col<self.rect.c1
        ):
            return rc

        index=self.cycle_index(
            rc
        )
        if index==0:
            return rc
        old=index-1
        new=self.forward_ring_index(
            old
        )
        return self.numbered_ring_coord(
            new
        )

    def inverse(
        self,
        rc:tuple[int,int],
    )->tuple[int,int]:
        if rc==self.rect.anchor:
            return rc

        row,col=rc
        if not (
            self.rect.r0<=row<self.rect.r1
            and self.rect.c0<=col<self.rect.c1
        ):
            return rc

        index=self.cycle_index(
            rc
        )
        if index==0:
            return rc
        post=index-1
        old=self.inverse_ring_index(
            post
        )
        return self.numbered_ring_coord(
            old
        )

    def rotated_payload(
        self,
        values:list[int]|tuple[int,...],
    )->tuple[int,...]:
        if len(values)!=self.numbered_ring_cells:
            raise ValueError(
                "Hamiltonian ring payload length mismatch"
            )
        k=self.effective_count
        return tuple(
            values[
                k:
            ]
        )+tuple(
            values[
                :k
            ]
        )

    def diagnostics(
        self,
    )->dict[str,object]:
        return {
            "rectangle":[
                self.rect.r0,
                self.rect.r1,
                self.rect.c0,
                self.rect.c1,
            ],
            "height":self.rect.height,
            "width":self.rect.width,
            "orientation":self.orientation,
            "cells":self.cells,
            "numberedRingCells":self.numbered_ring_cells,
            "requestedCount":self.count,
            "effectiveCount":self.effective_count,
            "loopPhysicalLength":self.loop_physical_length,
            "physicalLength":self.physical_length,
            "forwardComplexity":"O(1)",
            "inverseComplexity":"O(1)",
        }
