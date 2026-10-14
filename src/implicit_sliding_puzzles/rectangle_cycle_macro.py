#!/usr/bin/env python3
"""Compact legal rectangle-cycle blank macro.

A canonical clockwise cycle starts with the blank at the rectangle's top-left
corner and executes:

    R^(w-1) D^(h-1) L^(w-1) U^(h-1)

The blank returns to the same anchor.  Every numbered perimeter occupant moves
by exactly one position around the remaining perimeter ring; interior cells are
untouched.

Repeating the loop k times therefore has:

* a legal physical UDLR program represented as Repeat(loop,k);
* physical length k * 2*(h+w-2);
* O(1) grammar size;
* O(1) forward/inverse positional mapping via modular arithmetic.

This is the first scalable physical primitive for M9f3c block rotations.
"""

from __future__ import annotations

from dataclasses import dataclass

from .recursive_plan_grammar import (
    PlanNode,
    repeat,
    run,
    sequence,
)


@dataclass(frozen=True)
class Rectangle:
    r0:int
    r1:int
    c0:int
    c1:int

    def __post_init__(self)->None:
        if (
            self.r1-self.r0<2
            or self.c1-self.c0<2
        ):
            raise ValueError(
                "rectangle cycle requires height,width >=2"
            )

    @property
    def height(self)->int:
        return self.r1-self.r0

    @property
    def width(self)->int:
        return self.c1-self.c0

    @property
    def anchor(self)->tuple[int,int]:
        return self.r0,self.c0

    @property
    def perimeter_cells(self)->int:
        return 2*(
            self.height
            +self.width
        )-4

    @property
    def numbered_ring_cells(self)->int:
        # Anchor is occupied by the blank before and after every full cycle.
        return self.perimeter_cells-1


def clockwise_perimeter(
    rect:Rectangle,
)->tuple[tuple[int,int],...]:
    """Perimeter in blank-walk order, anchor first, without repeated anchor."""
    out=[]

    # top edge, left -> right
    for col in range(
        rect.c0,
        rect.c1,
    ):
        out.append(
            (
                rect.r0,
                col,
            )
        )

    # right edge, top+1 -> bottom
    for row in range(
        rect.r0+1,
        rect.r1,
    ):
        out.append(
            (
                row,
                rect.c1-1,
            )
        )

    # bottom edge, right-1 -> left
    for col in range(
        rect.c1-2,
        rect.c0-1,
        -1,
    ):
        out.append(
            (
                rect.r1-1,
                col,
            )
        )

    # left edge, bottom-1 -> top+1
    for row in range(
        rect.r1-2,
        rect.r0,
        -1,
    ):
        out.append(
            (
                row,
                rect.c0,
            )
        )

    expected=rect.perimeter_cells
    if (
        len(out)!=expected
        or len(
            set(
                out
            )
        )!=expected
        or out[
            0
        ]!=rect.anchor
    ):
        raise AssertionError(
            "rectangle perimeter construction drift"
        )
    return tuple(
        out
    )


def clockwise_loop_plan(
    rect:Rectangle,
)->PlanNode:
    """One full legal blank cycle returning to rect.anchor."""
    return sequence(
        run(
            "R",
            rect.width-1,
        ),
        run(
            "D",
            rect.height-1,
        ),
        run(
            "L",
            rect.width-1,
        ),
        run(
            "U",
            rect.height-1,
        ),
    )


@dataclass(frozen=True)
class RectangleCycle:
    rect:Rectangle
    count:int

    def __post_init__(self)->None:
        if self.count<0:
            raise ValueError(
                "rectangle cycle count cannot be negative"
            )

    @property
    def plan(self)->PlanNode:
        return repeat(
            clockwise_loop_plan(
                self.rect
            ),
            self.count,
        )

    @property
    def physical_length(self)->int:
        return (
            self.rect.perimeter_cells
            *self.count
        )

    def _ring_index(
        self,
        rc:tuple[int,int],
    )->int|None:
        """O(1) perimeter index in canonical clockwise blank-walk order."""
        row,col=rc
        rect=self.rect
        if (
            row<rect.r0
            or row>=rect.r1
            or col<rect.c0
            or col>=rect.c1
        ):
            return None

        h=rect.height
        w=rect.width

        if row==rect.r0:
            return col-rect.c0

        if col==rect.c1-1:
            return (
                w-1
                +(row-rect.r0)
            )

        if row==rect.r1-1:
            return (
                w+h-1
                +(rect.c1-2-col)
            )

        if col==rect.c0:
            return (
                2*w+h-2
                +(rect.r1-2-row)
            )

        return None

    def _coord_at_index(
        self,
        index:int,
    )->tuple[int,int]:
        """O(1) inverse of _ring_index for 0 <= index < perimeter_cells."""
        rect=self.rect
        p=rect.perimeter_cells
        if not 0<=index<p:
            raise IndexError(
                index
            )
        h=rect.height
        w=rect.width

        if index<w:
            return (
                rect.r0,
                rect.c0+index,
            )

        index-=w
        if index<h-1:
            return (
                rect.r0+1+index,
                rect.c1-1,
            )

        index-=h-1
        if index<w-1:
            return (
                rect.r1-1,
                rect.c1-2-index,
            )

        index-=w-1
        return (
            rect.r1-2-index,
            rect.c0,
        )

    def forward(
        self,
        rc:tuple[int,int],
    )->tuple[int,int]:
        """Map PRE coordinate to POST coordinate carrying its content."""
        if rc==self.rect.anchor:
            # The blank returns here.  No numbered content is assigned to the
            # anchor across a complete cycle.
            return rc

        index=self._ring_index(
            rc
        )
        if index is None:
            return rc
        if index==0:
            return rc

        m=self.rect.numbered_ring_cells
        old=index-1
        new=(
            old
            -(
                self.count%m
            )
        )%m
        return self._coord_at_index(
            new+1
        )

    def inverse(
        self,
        rc:tuple[int,int],
    )->tuple[int,int]:
        """Map POST coordinate back to PRE coordinate carrying its content."""
        if rc==self.rect.anchor:
            return rc

        index=self._ring_index(
            rc
        )
        if index is None:
            return rc
        if index==0:
            return rc

        m=self.rect.numbered_ring_cells
        post=index-1
        old=(
            post
            +(
                self.count%m
            )
        )%m
        return self._coord_at_index(
            old+1
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
            "perimeterCells":self.rect.perimeter_cells,
            "numberedRingCells":self.rect.numbered_ring_cells,
            "count":self.count,
            "physicalLength":self.physical_length,
            "grammarKind":self.plan.to_obj().get(
                "kind"
            ),
        }
