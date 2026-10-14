#!/usr/bin/env python3
"""Scale-independent physical plan grammar for Puzzle v0.13.

The million-side solver cannot represent its answer as one Python string per
physical blank move.  This module provides a tiny immutable grammar whose size
depends on structural plan complexity rather than expanded move count.

The first node set is intentionally small:

    Run(direction,count)
        one cardinal blank move repeated count times;

    PatternRepeat(pattern,count)
        one short literal pattern repeated count times;

    Sequence(children)
        concatenation with precomputed prefix lengths for O(log n) move_at();

    Repeat(child,count)
        structural repetition of an arbitrary child program.

All lengths are Python integers, so plans with 10^12+ physical moves are legal
objects.  materialize() is guarded and therefore cannot accidentally expand a
giant plan.  structural_digest() hashes the grammar itself, NOT the expanded
move stream; this is essential because hashing every physical move would retain
an unavoidable O(output length) cost.

The module deliberately does not replace the existing planner yet.  It is the
reference representation to which existing compact primitives are crosschecked
before production migration.
"""

from __future__ import annotations

import bisect
import hashlib
import json
from dataclasses import dataclass, field
from typing import Iterable, Iterator, Protocol


DIRS=frozenset("UDLR")


class PlanNode(Protocol):
    @property
    def physical_length(self)->int: ...

    def move_at(self,index:int)->str: ...

    def to_obj(self)->dict[str,object]: ...


@dataclass(frozen=True)
class Empty:
    @property
    def physical_length(self)->int:
        return 0

    def move_at(self,index:int)->str:
        raise IndexError(index)

    def to_obj(self)->dict[str,object]:
        return {"kind":"Empty"}


@dataclass(frozen=True)
class Run:
    direction:str
    count:int

    def __post_init__(self)->None:
        if self.direction not in DIRS:
            raise ValueError(
                f"invalid move direction {self.direction!r}"
            )
        if self.count<=0:
            raise ValueError("Run count must be positive")

    @property
    def physical_length(self)->int:
        return self.count

    def move_at(self,index:int)->str:
        if not 0<=index<self.count:
            raise IndexError(index)
        return self.direction

    def to_obj(self)->dict[str,object]:
        return {
            "kind":"Run",
            "direction":self.direction,
            "count":self.count,
        }


@dataclass(frozen=True)
class PatternRepeat:
    pattern:str
    count:int

    def __post_init__(self)->None:
        if not self.pattern:
            raise ValueError("PatternRepeat pattern must be nonempty")
        if any(move not in DIRS for move in self.pattern):
            raise ValueError(
                f"invalid move in pattern {self.pattern!r}"
            )
        if self.count<=0:
            raise ValueError(
                "PatternRepeat count must be positive"
            )

    @property
    def physical_length(self)->int:
        return len(self.pattern)*self.count

    def move_at(self,index:int)->str:
        if not 0<=index<self.physical_length:
            raise IndexError(index)
        return self.pattern[
            index%len(self.pattern)
        ]

    def to_obj(self)->dict[str,object]:
        return {
            "kind":"PatternRepeat",
            "pattern":self.pattern,
            "count":self.count,
        }


@dataclass(frozen=True)
class Sequence:
    children:tuple[PlanNode,...]
    _prefix:tuple[int,...]=field(
        init=False,
        repr=False,
        compare=False,
    )
    _length:int=field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self)->None:
        if not self.children:
            raise ValueError(
                "Sequence requires at least one child"
            )
        prefix=[]
        total=0
        for child in self.children:
            length=int(child.physical_length)
            if length<=0:
                raise ValueError(
                    "Sequence child must have positive length"
                )
            total+=length
            prefix.append(total)
        object.__setattr__(
            self,"_prefix",tuple(prefix)
        )
        object.__setattr__(
            self,"_length",total
        )

    @property
    def physical_length(self)->int:
        return self._length

    def move_at(self,index:int)->str:
        if not 0<=index<self._length:
            raise IndexError(index)
        child_index=bisect.bisect_right(
            self._prefix,index
        )
        start=(
            0
            if child_index==0
            else self._prefix[child_index-1]
        )
        return self.children[
            child_index
        ].move_at(index-start)

    def to_obj(self)->dict[str,object]:
        return {
            "kind":"Sequence",
            "children":[
                child.to_obj()
                for child in self.children
            ],
        }


@dataclass(frozen=True)
class Repeat:
    child:PlanNode
    count:int

    def __post_init__(self)->None:
        if self.child.physical_length<=0:
            raise ValueError(
                "Repeat child must have positive length"
            )
        if self.count<=0:
            raise ValueError(
                "Repeat count must be positive"
            )

    @property
    def physical_length(self)->int:
        return self.child.physical_length*self.count

    def move_at(self,index:int)->str:
        if not 0<=index<self.physical_length:
            raise IndexError(index)
        return self.child.move_at(
            index%self.child.physical_length
        )

    def to_obj(self)->dict[str,object]:
        return {
            "kind":"Repeat",
            "count":self.count,
            "child":self.child.to_obj(),
        }


EMPTY=Empty()


def run(
    direction:str,
    count:int,
)->PlanNode:
    if count<0:
        raise ValueError("run count cannot be negative")
    if count==0:
        return EMPTY
    return Run(direction,count)


def pattern_repeat(
    pattern:str,
    count:int,
)->PlanNode:
    if count<0:
        raise ValueError(
            "pattern repeat count cannot be negative"
        )
    if count==0:
        return EMPTY
    if len(pattern)==1:
        return Run(pattern,count)
    return PatternRepeat(pattern,count)


def repeat(
    child:PlanNode,
    count:int,
)->PlanNode:
    if count<0:
        raise ValueError(
            "repeat count cannot be negative"
        )
    if count==0 or child.physical_length==0:
        return EMPTY
    if count==1:
        return child
    if isinstance(child,Run):
        return Run(
            child.direction,
            child.count*count,
        )
    if isinstance(child,PatternRepeat):
        return PatternRepeat(
            child.pattern,
            child.count*count,
        )
    if isinstance(child,Repeat):
        return Repeat(
            child.child,
            child.count*count,
        )
    return Repeat(child,count)


def sequence(
    *nodes:PlanNode,
)->PlanNode:
    flat:list[PlanNode]=[]

    def add(node:PlanNode)->None:
        if node.physical_length==0:
            return
        if isinstance(node,Sequence):
            for child in node.children:
                add(child)
            return
        if (
            flat
            and isinstance(flat[-1],Run)
            and isinstance(node,Run)
            and flat[-1].direction==node.direction
        ):
            previous=flat.pop()
            assert isinstance(previous,Run)
            flat.append(
                Run(
                    node.direction,
                    previous.count+node.count,
                )
            )
            return
        flat.append(node)

    for node in nodes:
        add(node)

    if not flat:
        return EMPTY
    if len(flat)==1:
        return flat[0]
    return Sequence(tuple(flat))


def plan_from_moves(
    moves:str,
)->PlanNode:
    """Reference lift of an already-materialized move string.

    This is only a migration bridge.  Long-distance production primitives
    should emit Run/PatternRepeat/Repeat directly instead of first constructing
    the string.
    """
    if not moves:
        return EMPTY
    if any(move not in DIRS for move in moves):
        raise ValueError(
            "move string contains a non-cardinal symbol"
        )

    nodes:list[PlanNode]=[]
    start=0
    while start<len(moves):
        direction=moves[start]
        end=start+1
        while (
            end<len(moves)
            and moves[end]==direction
        ):
            end+=1
        nodes.append(
            Run(direction,end-start)
        )
        start=end
    return sequence(*nodes)


class PlanParts(list[str]):
    """Transitional dual recorder: legacy strings plus compact grammar.

    Existing solver code can keep append()/join()/sum(map(len,...)) semantics,
    while new compact producers call append_plan() to preserve their structural
    node before any legacy verification string is materialized.

    store_legacy=False is intentionally supported already, but production
    callers must migrate away from list-string consumers before enabling it.
    """

    def __init__(
        self,
        *,
        store_legacy:bool=True,
    ):
        super().__init__()
        self.store_legacy=store_legacy
        self._plan_nodes:list[PlanNode]=[]
        self._physical_length=0

    def append(self,moves:str)->None:  # type: ignore[override]
        if not isinstance(moves,str):
            raise TypeError(
                "PlanParts.append expects a physical move string; "
                "use append_plan for structural nodes"
            )
        node=plan_from_moves(moves)
        self._append_node(
            node,
            legacy_text=moves,
        )

    def append_plan(
        self,
        node:PlanNode,
        *,
        legacy_text:str|None=None,
    )->None:
        if self.store_legacy and legacy_text is None:
            raise ValueError(
                "dual-recording mode requires legacy_text for append_plan"
            )
        if legacy_text is not None:
            if len(legacy_text)!=node.physical_length:
                raise AssertionError(
                    "structural node length != legacy text length"
                )
            # Cheap exact guard for the migration phase.  Current compact
            # primitives are small enough on proof gates; million-scale callers
            # will set store_legacy=False and avoid this expansion entirely.
            for index,move in enumerate(legacy_text):
                if node.move_at(index)!=move:
                    raise AssertionError(
                        f"structural node != legacy stream at move {index}"
                    )
        self._append_node(
            node,
            legacy_text=legacy_text,
        )

    def _append_node(
        self,
        node:PlanNode,
        *,
        legacy_text:str|None,
    )->None:
        length=node.physical_length
        if length==0:
            if (
                self.store_legacy
                and legacy_text is not None
            ):
                super().append(legacy_text)
            return

        self._plan_nodes.append(node)
        self._physical_length+=length
        if self.store_legacy:
            assert legacy_text is not None
            super().append(legacy_text)

    @property
    def physical_length(self)->int:
        return self._physical_length

    @property
    def plan(self)->PlanNode:
        return sequence(*self._plan_nodes)

    @property
    def grammar_node_count(self)->int:
        return structural_node_count(
            self.plan
        )

    @property
    def grammar_depth(self)->int:
        return structural_depth(
            self.plan
        )

    @property
    def grammar_digest(self)->str:
        return structural_digest(
            self.plan
        )


def physical_length(node:PlanNode)->int:
    return int(node.physical_length)


def move_at(
    node:PlanNode,
    index:int,
)->str:
    return node.move_at(index)


def plan_from_obj(
    payload:dict[str,object],
)->PlanNode:
    """Decode canonical grammar JSON produced by to_obj()."""
    kind=payload.get("kind")
    if kind=="Empty":
        return EMPTY
    if kind=="Run":
        return Run(
            str(payload["direction"]),
            int(payload["count"]),
        )
    if kind=="PatternRepeat":
        return PatternRepeat(
            str(payload["pattern"]),
            int(payload["count"]),
        )
    if kind=="Sequence":
        children=payload.get("children")
        if not isinstance(children,list):
            raise ValueError(
                "Sequence children must be a list"
            )
        return sequence(*[
            plan_from_obj(child)
            for child in children
            if isinstance(child,dict)
        ])
    if kind=="Repeat":
        child=payload.get("child")
        if not isinstance(child,dict):
            raise ValueError(
                "Repeat child must be an object"
            )
        return repeat(
            plan_from_obj(child),
            int(payload["count"]),
        )
    raise ValueError(
        f"unknown plan grammar kind {kind!r}"
    )


def structural_node_count(
    node:PlanNode,
)->int:
    if isinstance(node,Empty):
        return 1
    if isinstance(node,Sequence):
        return 1+sum(
            structural_node_count(child)
            for child in node.children
        )
    if isinstance(node,Repeat):
        return 1+structural_node_count(
            node.child
        )
    return 1


def structural_depth(
    node:PlanNode,
)->int:
    if isinstance(node,Sequence):
        return 1+max(
            structural_depth(child)
            for child in node.children
        )
    if isinstance(node,Repeat):
        return 1+structural_depth(
            node.child
        )
    return 1


def structural_digest(
    node:PlanNode,
)->str:
    """SHA-256 of canonical grammar JSON, independent of expanded length."""
    payload=json.dumps(
        node.to_obj(),
        sort_keys=True,
        separators=(",",":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def materialize(
    node:PlanNode,
    *,
    max_moves:int=100_000,
)->str:
    total=node.physical_length
    if total>max_moves:
        raise ValueError(
            f"refusing to materialize {total} physical moves"
        )
    return "".join(
        node.move_at(i)
        for i in range(total)
    )


def iter_moves(
    node:PlanNode,
    *,
    start:int=0,
    stop:int|None=None,
)->Iterator[str]:
    total=node.physical_length
    if stop is None:
        stop=total
    if not (
        0<=start<=stop<=total
    ):
        raise IndexError(
            (start,stop,total)
        )
    for index in range(start,stop):
        yield node.move_at(index)


def stage_nodes_to_plan(
    nodes:Iterable[object],
)->PlanNode:
    """Losslessly lift compact StageToPort AST nodes into the global grammar."""
    out:list[PlanNode]=[]
    for node in nodes:
        kind=getattr(node,"kind")
        direction=str(
            getattr(node,"direction")
        )
        count=int(
            getattr(node,"count")
        )
        pattern=str(
            getattr(node,"pattern")
        )

        if kind=="BlankRun":
            out.append(
                run(direction,count)
            )
        elif kind=="AdvanceRun":
            out.append(
                pattern_repeat(
                    pattern,count
                )
            )
        elif kind=="AdvanceFinish":
            out.append(
                run(direction,count)
            )
        else:
            raise ValueError(
                f"unsupported StageToPort node kind {kind!r}"
            )
    return sequence(*out)
