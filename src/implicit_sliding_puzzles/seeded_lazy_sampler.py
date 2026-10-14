#!/usr/bin/env python3
"""M2 candidate: scalable query-order-independent seeded lazy permutation.

The small reference in lazy_uniform_permutation.py samples Hypergeometric
splits with exact combinatorial weights by enumerating the complete support.
That is a proof oracle, not a trillion-cell implementation.

This module keeps the SAME recursive permutation model but changes two backend
details required by production scaling:

1. large Hypergeometric splits use Stadlober's HRUA ratio-of-uniforms method;
2. every split owns a deterministic PRNG stream derived from
   (global seed, permutation node, subset node).

Therefore the board is a concrete function of the seed and node addresses,
rather than of query order. Asking B before A cannot change the eventual board.

For small edge samples (<10 items, or complement <10), an integer without-
replacement sampler is used. HRUA is the same algorithm family used by common
numerical libraries for large Hypergeometric variates. The original
exact-combinatorial sampler remains the mathematical small-domain oracle.

Important precision boundary:
HRUA uses IEEE-754 log-gamma / ratio-of-uniforms acceptance arithmetic. This is
the production-speed candidate, not a claim of bit-for-bit exact rational
sampling at 10^12. Small-domain distribution and full-permutation regressions
therefore remain mandatory while this backend is evaluated.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from collections import Counter
from dataclasses import dataclass


D1=1.7155277699214135   # 2*sqrt(2/e)
D2=0.8989161620588988   # 3-2*sqrt(3/e)


class NodeRandom:
    """Counter PRNG keyed by seed + immutable integer node address."""

    def __init__(self,seed:int,key:tuple[int,...]):
        if seed<0:
            raise ValueError("seed must be nonnegative")
        self.seed=seed
        self.key=key
        self.counter=0
        self.words=0

    def _word(self)->int:
        h=hashlib.blake2b(digest_size=8,person=b"PZL-M2-H")
        h.update(self.seed.to_bytes(16,"little",signed=False))
        for value in self.key:
            h.update(int(value).to_bytes(16,"little",signed=True))
        h.update(self.counter.to_bytes(8,"little",signed=False))
        self.counter+=1
        self.words+=1
        return int.from_bytes(h.digest(),"little")

    def randbelow(self,upper:int)->int:
        """Uniform integer in [0, upper) by rejection, for arbitrary Python int."""
        if upper<=0:
            raise ValueError("upper must be positive")
        bits=max(1,(upper-1).bit_length())
        words=(bits+63)//64
        mask=(1<<bits)-1
        while True:
            value=0
            for i in range(words):
                value|=self._word()<<(64*i)
            value&=mask
            if value<upper:
                return value

    def uniform_open(self)->float:
        """Deterministic 53-bit float strictly inside (0,1)."""
        mantissa=self._word()>>11
        return (mantissa+0.5)/(1<<53)


@dataclass
class SamplerStats:
    hypergeometric_calls:int=0
    small_without_replacement_calls:int=0
    hrua_calls:int=0
    hrua_proposals:int=0
    random_words:int=0

    def as_dict(self)->dict[str,int|float]:
        return {
            "hypergeometricCalls":self.hypergeometric_calls,
            "smallWithoutReplacementCalls":self.small_without_replacement_calls,
            "hruaCalls":self.hrua_calls,
            "hruaProposals":self.hrua_proposals,
            "averageHruaProposals":(
                self.hrua_proposals/self.hrua_calls
                if self.hrua_calls else 0.0
            ),
            "randomWords":self.random_words,
        }


def _small_hypergeometric(
    rng:NodeRandom,
    good:int,
    bad:int,
    sample:int,
)->int:
    """Exact integer sampling by explicit draws; only used for tiny sample tails."""
    total=good+bad
    remaining_sample=min(sample,total-sample)
    remaining_total=total
    remaining_good=good

    while (
        remaining_sample>0
        and remaining_good>0
        and remaining_total>remaining_good
    ):
        remaining_total-=1
        if rng.randbelow(remaining_total+1)<remaining_good:
            remaining_good-=1
        remaining_sample-=1

    if remaining_total==remaining_good:
        remaining_good-=remaining_sample

    return remaining_good if sample>total//2 else good-remaining_good


def _logfactorial(n:int)->float:
    if n<0:
        raise ValueError("factorial argument must be nonnegative")
    return math.lgamma(float(n)+1.0)


def _hrua(
    rng:NodeRandom,
    good:int,
    bad:int,
    sample:int,
)->tuple[int,int]:
    """Stadlober HRUA Hypergeometric variate; return (value, proposal_count)."""
    popsize=good+bad
    computed_sample=min(sample,popsize-sample)
    mingoodbad=min(good,bad)
    maxgoodbad=max(good,bad)

    p=mingoodbad/popsize
    q=maxgoodbad/popsize
    mu=computed_sample*p
    a=mu+0.5
    variance=(
        (popsize-computed_sample)
        * computed_sample
        * p
        * q
        / (popsize-1)
    )
    c=math.sqrt(variance+0.5)
    h=D1*c+D2

    # Integer arithmetic avoids losing the floor through a 1e24 intermediate.
    mode=((computed_sample+1)*(mingoodbad+1))//(popsize+2)

    g=(
        _logfactorial(mode)
        +_logfactorial(mingoodbad-mode)
        +_logfactorial(computed_sample-mode)
        +_logfactorial(maxgoodbad-computed_sample+mode)
    )
    upper=min(
        min(computed_sample,mingoodbad)+1.0,
        math.floor(a+16*c),
    )

    proposals=0
    while True:
        proposals+=1
        u=rng.uniform_open()
        v=rng.uniform_open()
        x=a+h*(v-0.5)/u
        if x<0.0 or x>=upper:
            continue

        k=math.floor(x)
        gp=(
            _logfactorial(k)
            +_logfactorial(mingoodbad-k)
            +_logfactorial(computed_sample-k)
            +_logfactorial(maxgoodbad-computed_sample+k)
        )
        t=g-gp

        if u*(4.0-u)-3.0<=t:
            break
        if u*(u-t)>=1.0:
            continue
        if 2.0*math.log(u)<=t:
            break

    if good>bad:
        k=computed_sample-k
    if computed_sample<sample:
        k=good-k
    return int(k),proposals


def seeded_hypergeometric(
    seed:int,
    key:tuple[int,...],
    population:int,
    successes:int,
    draws:int,
    stats:SamplerStats|None=None,
)->int:
    if not (
        0<=successes<=population
        and 0<=draws<=population
    ):
        raise ValueError("invalid Hypergeometric parameters")

    if stats is not None:
        stats.hypergeometric_calls+=1

    lo=max(0,successes-(population-draws))
    hi=min(successes,draws)
    if lo==hi:
        return lo

    rng=NodeRandom(seed,key)
    if draws<10 or population-draws<10:
        value=_small_hypergeometric(
            rng,successes,population-successes,draws
        )
        proposals=0
        if stats is not None:
            stats.small_without_replacement_calls+=1
    else:
        value,proposals=_hrua(
            rng,successes,population-successes,draws
        )
        if stats is not None:
            stats.hrua_calls+=1
            stats.hrua_proposals+=proposals

    if not lo<=value<=hi:
        raise AssertionError(
            f"Hypergeometric sample outside support: {value} not {lo}..{hi}"
        )
    if stats is not None:
        stats.random_words+=rng.words
    return value


@dataclass
class _SubsetNode:
    start:int
    length:int
    selected:int
    children:tuple["_SubsetNode","_SubsetNode"]|None=None


class SeededLazySubset:
    def __init__(
        self,
        n:int,
        k:int,
        seed:int,
        key_prefix:tuple[int,...],
        stats:SamplerStats,
    ):
        if not 0<=k<=n:
            raise ValueError("subset size outside domain")
        self.n=n
        self.k=k
        self.seed=seed
        self.key_prefix=key_prefix
        self.stats=stats
        self.root=_SubsetNode(0,n,k)
        self.materialized_splits=0

    def _split(self,node:_SubsetNode)->tuple[_SubsetNode,_SubsetNode]:
        if node.length<=1:
            raise ValueError("cannot split subset leaf")
        if node.children is None:
            left_len=node.length//2
            left_selected=seeded_hypergeometric(
                self.seed,
                self.key_prefix+(
                    node.start,
                    node.length,
                    node.selected,
                ),
                node.length,
                node.selected,
                left_len,
                self.stats,
            )
            node.children=(
                _SubsetNode(node.start,left_len,left_selected),
                _SubsetNode(
                    node.start+left_len,
                    node.length-left_len,
                    node.selected-left_selected,
                ),
            )
            self.materialized_splits+=1
        return node.children

    def classify(self,position:int)->tuple[bool,int]:
        if not 0<=position<self.n:
            raise IndexError(position)
        node=self.root
        selected_before=0
        unselected_before=0
        while node.length>1:
            left,right=self._split(node)
            if position<right.start:
                node=left
            else:
                selected_before+=left.selected
                unselected_before+=left.length-left.selected
                node=right
        selected=node.selected==1
        return (
            selected,
            selected_before if selected else unselected_before,
        )

    def select(self,selected:bool,rank:int)->int:
        total=self.k if selected else self.n-self.k
        if not 0<=rank<total:
            raise IndexError(rank)
        node=self.root
        local=rank
        while node.length>1:
            left,right=self._split(node)
            count=left.selected if selected else left.length-left.selected
            if local<count:
                node=left
            else:
                local-=count
                node=right
        return node.start

    def count_before(self,selected:bool,end:int)->int:
        if end<=0:
            return 0
        if end>=self.n:
            return self.k if selected else self.n-self.k
        node=self.root
        count=0
        while node.length>1:
            left,right=self._split(node)
            if end<=right.start:
                node=left
            else:
                count+=left.selected if selected else left.length-left.selected
                node=right
        if end>node.start:
            count+=node.selected if selected else 1-node.selected
        return count


class SeededLazyPermutation:
    """Recursive-interleaving permutation with node-addressed seeded splits."""

    def __init__(
        self,
        n:int,
        seed:int,
        offset:int=0,
        stats:SamplerStats|None=None,
    ):
        if n<=0:
            raise ValueError("n must be positive")
        self.n=n
        self.seed=seed
        self.offset=offset
        self.stats=stats if stats is not None else SamplerStats()
        self._routing:SeededLazySubset|None=None
        self._left:SeededLazyPermutation|None=None
        self._right:SeededLazyPermutation|None=None

    def _ensure_routing(self)->None:
        if self.n>1 and self._routing is None:
            left_n=self.n//2
            self._routing=SeededLazySubset(
                self.n,
                left_n,
                self.seed,
                # 0x52 separates routing-node keys from future namespaces.
                (0x52,self.offset,self.n),
                self.stats,
            )

    def value_at(self,position:int)->int:
        if not 0<=position<self.n:
            raise IndexError(position)
        if self.n==1:
            return self.offset
        self._ensure_routing()
        assert self._routing is not None
        left_n=self.n//2
        goes_left,rank=self._routing.classify(position)
        if goes_left:
            if self._left is None:
                self._left=SeededLazyPermutation(
                    left_n,self.seed,self.offset,self.stats
                )
            return self._left.value_at(rank)
        if self._right is None:
            self._right=SeededLazyPermutation(
                self.n-left_n,self.seed,self.offset+left_n,self.stats
            )
        return self._right.value_at(rank)

    def position_of(self,value:int)->int:
        if not self.offset<=value<self.offset+self.n:
            raise IndexError(value)
        if self.n==1:
            return 0
        self._ensure_routing()
        assert self._routing is not None
        left_n=self.n//2
        if value<self.offset+left_n:
            if self._left is None:
                self._left=SeededLazyPermutation(
                    left_n,self.seed,self.offset,self.stats
                )
            child=self._left.position_of(value)
            return self._routing.select(True,child)
        if self._right is None:
            self._right=SeededLazyPermutation(
                self.n-left_n,self.seed,self.offset+left_n,self.stats
            )
        child=self._right.position_of(value)
        return self._routing.select(False,child)

    def count_values(
        self,
        output_start:int,
        output_length:int,
        value_lo:int,
        value_hi:int,
    )->int:
        if (
            output_length<0
            or output_start<0
            or output_start+output_length>self.n
        ):
            raise ValueError("output interval outside permutation")
        if output_length==0 or value_hi<=value_lo:
            return 0
        lo=max(value_lo,self.offset)
        hi=min(value_hi,self.offset+self.n)
        if hi<=lo:
            return 0
        if lo<=self.offset and hi>=self.offset+self.n:
            return output_length
        if self.n==1:
            return output_length if lo<=self.offset<hi else 0

        self._ensure_routing()
        assert self._routing is not None
        left_n=self.n//2
        boundary=self.offset+left_n

        left_begin=self._routing.count_before(True,output_start)
        left_end=self._routing.count_before(
            True,output_start+output_length
        )
        right_begin=self._routing.count_before(False,output_start)
        right_end=self._routing.count_before(
            False,output_start+output_length
        )

        total=0
        if left_end>left_begin and lo<boundary:
            if self._left is None:
                self._left=SeededLazyPermutation(
                    left_n,self.seed,self.offset,self.stats
                )
            total+=self._left.count_values(
                left_begin,left_end-left_begin,lo,min(hi,boundary)
            )
        if right_end>right_begin and hi>boundary:
            if self._right is None:
                self._right=SeededLazyPermutation(
                    self.n-left_n,
                    self.seed,
                    boundary,
                    self.stats,
                )
            total+=self._right.count_values(
                right_begin,right_end-right_begin,max(lo,boundary),hi
            )
        return total

    def materialize(self)->list[int]:
        return [self.value_at(i) for i in range(self.n)]

    def materialized_split_count(self)->int:
        total=(
            0 if self._routing is None
            else self._routing.materialized_splits
        )
        if self._left is not None:
            total+=self._left.materialized_split_count()
        if self._right is not None:
            total+=self._right.materialized_split_count()
        return total


def distribution_smoke(trials:int=24_000)->dict[str,object]:
    counts:Counter[tuple[int,...]]=Counter()
    for seed in range(trials):
        p=SeededLazyPermutation(4,seed).materialize()
        counts[tuple(p)]+=1
    if len(counts)!=24:
        raise AssertionError("seeded sampler missed a 4! outcome")
    expected=trials/24
    chi=sum((n-expected)**2/expected for n in counts.values())
    if chi>=70.0:
        raise AssertionError(f"4! distribution smoke too uneven: {chi}")
    return {
        "domain":4,
        "trials":trials,
        "outcomesSeen":len(counts),
        "chiSquare":chi,
        "threshold":70.0,
    }


def query_order_audit()->dict[str,object]:
    n=1024
    seed=0x620002
    positions=[0,1,17,511,512,777,1023,333,900]
    ranges=[
        (0,128,0,256),
        (300,211,500,900),
        (700,324,0,512),
        (128,512,200,800),
    ]

    a=SeededLazyPermutation(n,seed)
    aval=[a.value_at(p) for p in positions]
    acount=[
        a.count_values(*q)
        for q in ranges
    ]

    b=SeededLazyPermutation(n,seed)
    bcount=[
        b.count_values(*q)
        for q in reversed(ranges)
    ][::-1]
    bval=[
        b.value_at(p)
        for p in reversed(positions)
    ][::-1]

    if aval!=bval or acount!=bcount:
        raise AssertionError("query order changed observable answers")

    full_a=a.materialize()
    full_b=b.materialize()
    if full_a!=full_b:
        raise AssertionError("query order changed final permutation")
    if sorted(full_a)!=list(range(n)):
        raise AssertionError("seeded materialization is not a permutation")

    for pos,value in enumerate(full_a):
        if a.position_of(value)!=pos:
            raise AssertionError("seeded inverse query failed")

    for query,expected in zip(ranges,acount,strict=True):
        start,length,lo,hi=query
        dense=sum(lo<=x<hi for x in full_a[start:start+length])
        if dense!=expected:
            raise AssertionError("aggregate query != dense seeded completion")

    return {
        "domain":n,
        "seed":seed,
        "positionsChecked":len(positions),
        "rangesChecked":len(ranges),
        "queryOrderIndependent":True,
        "finalPermutationIndependentOfQueryOrder":True,
        "aggregateMatchesDense":True,
        "inverseVerified":True,
        "materializedSplits":a.materialized_split_count(),
        "sampler":a.stats.as_dict(),
    }


def huge_hypergeometric_audit(samples:int=2000)->dict[str,object]:
    population=1_000_000_000_000
    successes=population//2
    draws=population//2
    stats=SamplerStats()
    values=[]
    started=time.perf_counter()
    for seed in range(samples):
        values.append(seeded_hypergeometric(
            seed,
            (0x4847,population,successes,draws),
            population,
            successes,
            draws,
            stats,
        ))
    elapsed=time.perf_counter()-started

    mean=sum(values)/samples
    expected=draws*(successes/population)
    variance=(
        draws
        *(successes/population)
        *(1-successes/population)
        *((population-draws)/(population-1))
    )
    standard_error=math.sqrt(variance/samples)
    if abs(mean-expected)>8*standard_error:
        raise AssertionError(
            f"huge Hypergeometric mean drift: {mean} vs {expected}"
        )
    if stats.hrua_calls!=samples:
        raise AssertionError("huge audit unexpectedly left HRUA path")
    if stats.hrua_proposals>10*samples:
        raise AssertionError("HRUA proposal count unexpectedly high")

    return {
        "population":population,
        "successes":successes,
        "draws":draws,
        "samples":samples,
        "mean":mean,
        "expectedMean":expected,
        "standardError":standard_error,
        "meanWithinEightStandardErrors":True,
        "elapsedSeconds":elapsed,
        "samplesPerSecond":samples/elapsed if elapsed else None,
        "sampler":stats.as_dict(),
    }


def trillion_sparse_tree_audit()->dict[str,object]:
    n=1_000_000_000_000
    seed=0x620012
    oracle=SeededLazyPermutation(n,seed)

    # One enormous half-vs-half aggregate query exercises 10^12 arithmetic
    # without materializing either side.
    count=oracle.count_values(
        0,n//2,
        0,n//2,
    )
    lo=0
    hi=n//2
    if not lo<=count<=hi:
        raise AssertionError("trillion aggregate count outside support")

    before=oracle.stats.hypergeometric_calls
    same=oracle.count_values(
        0,n//2,
        0,n//2,
    )
    after=oracle.stats.hypergeometric_calls
    if same!=count or after!=before:
        raise AssertionError("repeated trillion query consumed new splits")

    # Sparse exact leaf and inverse are allowed to refine one path.
    position=987_654_321_012
    value=oracle.value_at(position)
    if oracle.position_of(value)!=position:
        raise AssertionError("trillion sparse inverse failed")

    return {
        "logicalDomain":n,
        "seed":seed,
        "halfVsHalfCount":count,
        "repeatAggregateConsumedNoNewSplits":True,
        "sparsePosition":position,
        "sparseValue":value,
        "sparseInverseVerified":True,
        "materializedSplits":oracle.materialized_split_count(),
        "sampler":oracle.stats.as_dict(),
        "densePermutationMaterialized":False,
    }


def run()->dict[str,object]:
    return {
        "status":"ok",
        "gate":"M2-seeded-scalable-lazy-sampler-candidate",
        "distributionSmoke":distribution_smoke(),
        "queryOrder":query_order_audit(),
        "hugeHypergeometric":huge_hypergeometric_audit(),
        "trillionSparseTree":trillion_sparse_tree_audit(),
        "precisionBoundary":(
            "large splits use floating HRUA/log-gamma; keep the exact "
            "small-domain combinatorial oracle as the distribution reference"
        ),
        "nextGate":(
            "attach this backend to SpatialRadixOrder, then measure arbitrary-seed "
            "root flow and SolveRegion rather than isolated sampler calls"
        ),
    }


if __name__=="__main__":
    print(json.dumps(run(),indent=2))
