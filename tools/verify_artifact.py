#!/usr/bin/env python3
"""Standalone validation of the serialised grammar and pinned artifact hash.

This program imports NOTHING from the implementation of the puzzle generator.
It does not claim to prove that a trillion-step program is physically legal;
that requires the construction proof and the primitive-level obligations.
"""
from __future__ import annotations
import argparse
import bisect
import hashlib
import json
from pathlib import Path
import sys

DIRECTIONS=set("UDLR")
MAX_ARTIFACT_BYTES=8_000_000
MAX_NODES=100_000
MAX_DEPTH=64

def canonical(data, *, utf8=False):
    return json.dumps(data,sort_keys=True,separators=(",",":"),ensure_ascii=not utf8).encode("utf-8")

def digest(data, *, utf8=False):
    return hashlib.sha256(canonical(data,utf8=utf8)).hexdigest()

def validate_node(node, stats, depth=1):
    if not isinstance(node,dict) or depth > MAX_DEPTH:
        raise ValueError("invalid grammar node or excessive depth")
    stats["nodes"]+=1
    if stats["nodes"] > MAX_NODES:
        raise ValueError("grammar exceeds node limit")
    stats["depth"]=max(stats["depth"],depth)
    kind=node.get("kind")
    if kind=="Empty":
        if set(node)!={"kind"}: raise ValueError("malformed Empty")
        return 0
    if kind=="Run":
        if set(node)!={"kind","direction","count"}: raise ValueError("malformed Run")
        d,k=node["direction"],node["count"]
        if not isinstance(d,str) or d not in DIRECTIONS or type(k) is not int or k<=0:
            raise ValueError("invalid Run")
        return k
    if kind=="PatternRepeat":
        if set(node)!={"kind","pattern","count"}: raise ValueError("malformed PatternRepeat")
        pat,k=node["pattern"],node["count"]
        if not isinstance(pat,str) or not pat or any(x not in DIRECTIONS for x in pat) or type(k) is not int or k<=0:
            raise ValueError("invalid PatternRepeat")
        return len(pat)*k
    if kind=="Repeat":
        if set(node)!={"kind","child","count"}: raise ValueError("malformed Repeat")
        k=node["count"]
        if type(k) is not int or k<=0: raise ValueError("invalid Repeat")
        child_len=validate_node(node["child"],stats,depth+1)
        if child_len<=0: raise ValueError("empty repetition")
        return k*child_len
    if kind=="Sequence":
        if set(node)!={"kind","children"}: raise ValueError("malformed Sequence")
        ch=node["children"]
        if not isinstance(ch,list) or not ch: raise ValueError("empty Sequence")
        lengths=[validate_node(item,stats,depth+1) for item in ch]
        if any(x<=0 for x in lengths): raise ValueError("empty Sequence child")
        return sum(lengths)
    raise ValueError("unknown grammar node")

def move_at(node,index):
    kind=node["kind"]
    if kind=="Run": return node["direction"]
    if kind=="PatternRepeat": return node["pattern"][index%len(node["pattern"])]
    if kind=="Repeat":
        child=node["child"]
        return move_at(child,index%node_length(child))
    if kind=="Sequence":
        ch=node["children"]
        totals=[]
        acc=0
        for item in ch:
            acc+=node_length(item)
            totals.append(acc)
        child_index=bisect.bisect_right(totals,index)
        offset=0 if child_index==0 else totals[child_index-1]
        return move_at(ch[child_index],index-offset)
    raise ValueError("No moves in grammar node")

def node_length(node):
    # Pure structural evaluation, independent of the production code.
    kind=node["kind"]
    if kind=="Empty": return 0
    if kind=="Run": return node["count"]
    if kind=="PatternRepeat": return len(node["pattern"])*node["count"]
    if kind=="Repeat": return node["count"]*node_length(node["child"])
    if kind=="Sequence": return sum(node_length(x) for x in node["children"])
    raise ValueError("unknown grammar node")

def verify(path, expected_sha=None, indices=None):
    if path.stat().st_size>MAX_ARTIFACT_BYTES: raise ValueError("oversized artifact")
    data=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data,dict): raise ValueError("non-object artifact")
    source_sha=data.get("artifactSha256")
    core={k:v for k,v in data.items() if k!="artifactSha256"}
    if not isinstance(source_sha,str) or digest(core,utf8=True)!=source_sha:
        raise ValueError("artifact SHA-256 mismatch")
    if expected_sha is not None and expected_sha!=source_sha:
        raise ValueError("pinned SHA-256 mismatch")
    if data.get("format")!="puzzle-million-solution" or data.get("version")!=1:
        raise ValueError("unknown artifact format")
    profile=data.get("profile")
    if not isinstance(profile,dict) or profile.get("side")!=1_000_000 or profile.get("cells")!=10**12:
        raise ValueError("unexpected million-board profile")
    solution=data.get("solution")
    if not isinstance(solution,dict) or not isinstance(solution.get("grammar"),dict):
        raise ValueError("missing grammar")
    grammar=solution["grammar"]
    stats={"nodes":0,"depth":0}
    length=validate_node(grammar,stats)
    if solution.get("physicalLength")!=length: raise ValueError("physical length mismatch")
    if solution.get("grammarNodes")!=stats["nodes"]: raise ValueError("node count mismatch")
    if solution.get("grammarDepth")!=stats["depth"]: raise ValueError("grammar depth mismatch")
    if solution.get("grammarDigest")!=digest(grammar): raise ValueError("grammar digest mismatch")
    probes=[]
    for index in (indices or []):
        if not 0<=index<length: raise ValueError("probe outside physical length")
        probes.append({"index":index,"move":move_at(grammar,index)})
    return {"status":"ok","artifactSha256":source_sha,"physicalLength":length,
            "grammarNodes":stats["nodes"],"grammarDepth":stats["depth"],
            "sampledMoves":probes,"scope":"integrity and exact grammar semantics only"}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact",type=Path)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--indices",default="0,1")
    args=parser.parse_args()
    indices=[int(x) for x in args.indices.split(",") if x.strip()]
    try:
        result=verify(args.artifact,args.expected_sha256,indices)
        print(json.dumps(result,indent=2))
    except (ValueError,IndexError,OSError,TypeError,KeyError,RecursionError) as exc:
        print(f"verification FAILED: {exc}",file=sys.stderr)
        sys.exit(1)

if __name__=="__main__":
    main()
