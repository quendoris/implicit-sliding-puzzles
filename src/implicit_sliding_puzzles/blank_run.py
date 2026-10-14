"""Constant-space positional transforms for a legal straight blank run.

For a path p[0], ..., p[k], a blank starting at p[0] exchanges positions
with each successive neighbour. Its induced permutation is:
    p[0] -> p[k];  p[i] -> p[i-1] for 1 <= i <= k.
Outside positions are unchanged.
"""
from __future__ import annotations
from dataclasses import dataclass

DIRECTIONS = {"U":(-1,0),"D":(1,0),"L":(0,-1),"R":(0,1)}

@dataclass(frozen=True)
class BlankRunTransform:
    start: tuple[int,int]
    direction: str
    count: int

    def __post_init__(self)->None:
        if self.direction not in DIRECTIONS:
            raise ValueError(f"Invalid direction: {self.direction!r}")
        if self.count < 0:
            raise ValueError("Negative blank-run length")

    @property
    def end(self)->tuple[int,int]:
        dr,dc=DIRECTIONS[self.direction]
        return (self.start[0]+self.count*dr, self.start[1]+self.count*dc)

    def point(self,index:int)->tuple[int,int]:
        if not 0 <= index <= self.count:
            raise IndexError(index)
        dr,dc=DIRECTIONS[self.direction]
        return (self.start[0]+index*dr,self.start[1]+index*dc)

    def path_index(self,rc:tuple[int,int])->int|None:
        dr,dc=DIRECTIONS[self.direction]
        delta=(rc[0]-self.start[0], rc[1]-self.start[1])
        index=delta[0]*dr+delta[1]*dc
        if delta == (dr*index,dc*index) and 0 <= index <= self.count:
            return index
        return None

def forward_blank_run(transform:BlankRunTransform,rc:tuple[int,int])->tuple[int,int]:
    index=transform.path_index(rc)
    if index is None:
        return rc
    return transform.point(transform.count if index==0 else index-1)

def inverse_blank_run(transform:BlankRunTransform,rc:tuple[int,int])->tuple[int,int]:
    index=transform.path_index(rc)
    if index is None:
        return rc
    return transform.point(0 if index==transform.count else index+1)
