#!/usr/bin/env python3
"""Portable production artifact for the frozen million-side legal puzzle.

One artifact stores:
* the frozen board profile and seed;
* exact final blank coordinate;
* compact exact solution grammar Q(seed)^-1;
* physical length and structural metrics;
* independent scramble/solution grammar digests;
* an artifact SHA-256 over canonical JSON payload.

No board cell array and no expanded U/D/L/R move stream is stored.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .canonical_million_legal_board import (
    CANONICAL_MILLION_ANCHOR_MODE,
    CANONICAL_MILLION_CELLS,
    CANONICAL_MILLION_ROUNDS,
    CANONICAL_MILLION_SIDE,
    CANONICAL_PROFILE_NAME,
    build_canonical_million_board,
    profile_manifest,
)
from .recursive_plan_grammar import (
    plan_from_obj,
    structural_depth,
    structural_digest,
    structural_node_count,
)


ARTIFACT_FORMAT='puzzle-million-solution'
ARTIFACT_VERSION=1


def _canonical_json_bytes(payload:dict[str,Any])->bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(',',':'),
        ensure_ascii=False,
    ).encode('utf-8')


def _payload_digest(payload:dict[str,Any])->str:
    return hashlib.sha256(
        _canonical_json_bytes(payload)
    ).hexdigest()


def build_solution_artifact(seed:int)->dict[str,Any]:
    """Build one deterministic compact solution artifact for seed."""
    board=build_canonical_million_board(seed)
    solution_obj=board.solution_plan.to_obj()

    core={
        'format':ARTIFACT_FORMAT,
        'version':ARTIFACT_VERSION,
        'profile':profile_manifest(),
        'seed':int(seed),
        'finalBlank':list(board.final_blank),
        'solution':{
            'grammar':solution_obj,
            'physicalLength':board.solution_plan.physical_length,
            'grammarNodes':structural_node_count(board.solution_plan),
            'grammarDepth':structural_depth(board.solution_plan),
            'grammarDigest':structural_digest(board.solution_plan),
        },
        'scrambleGrammarDigest':structural_digest(board.scramble_plan),
        'materializedBoardCells':0,
        'materializedPhysicalMoves':0,
    }
    artifact=dict(core)
    artifact['artifactSha256']=_payload_digest(core)
    return artifact


def verify_solution_artifact(
    artifact:dict[str,Any],
)->dict[str,Any]:
    """Verify format, integrity, profile, and exact grammar against seed."""
    if artifact.get('format')!=ARTIFACT_FORMAT:
        raise ValueError('wrong artifact format')
    if int(artifact.get('version',-1))!=ARTIFACT_VERSION:
        raise ValueError('unsupported artifact version')

    supplied_digest=artifact.get('artifactSha256')
    if not isinstance(supplied_digest,str):
        raise ValueError('artifactSha256 missing')
    core={
        key:value
        for key,value in artifact.items()
        if key!='artifactSha256'
    }
    calculated=_payload_digest(core)
    if calculated!=supplied_digest:
        raise ValueError('artifact SHA-256 mismatch')

    expected_profile=profile_manifest()
    if artifact.get('profile')!=expected_profile:
        raise ValueError('frozen million profile mismatch')

    seed=int(artifact['seed'])
    board=build_canonical_million_board(seed)

    blank=artifact.get('finalBlank')
    if blank!=list(board.final_blank):
        raise ValueError('final blank mismatch')

    solution=artifact.get('solution')
    if not isinstance(solution,dict):
        raise ValueError('solution object missing')
    grammar=solution.get('grammar')
    if not isinstance(grammar,dict):
        raise ValueError('solution grammar missing')

    decoded=plan_from_obj(grammar)
    expected=board.solution_plan

    if decoded.to_obj()!=expected.to_obj():
        raise ValueError('decoded grammar is not exact frozen Q^-1')
    if decoded.physical_length!=expected.physical_length:
        raise ValueError('solution physical length mismatch')
    if int(solution.get('physicalLength',-1))!=expected.physical_length:
        raise ValueError('stored physical length mismatch')

    nodes=structural_node_count(decoded)
    depth=structural_depth(decoded)
    digest=structural_digest(decoded)
    if int(solution.get('grammarNodes',-1))!=nodes:
        raise ValueError('stored grammar node count mismatch')
    if int(solution.get('grammarDepth',-1))!=depth:
        raise ValueError('stored grammar depth mismatch')
    if solution.get('grammarDigest')!=digest:
        raise ValueError('stored solution grammar digest mismatch')
    if artifact.get('scrambleGrammarDigest')!=structural_digest(board.scramble_plan):
        raise ValueError('stored scramble grammar digest mismatch')
    if int(artifact.get('materializedBoardCells',-1))!=0:
        raise ValueError('artifact claims materialized board cells')
    if int(artifact.get('materializedPhysicalMoves',-1))!=0:
        raise ValueError('artifact claims materialized physical moves')

    return {
        'status':'ok',
        'format':ARTIFACT_FORMAT,
        'version':ARTIFACT_VERSION,
        'profile':CANONICAL_PROFILE_NAME,
        'seed':seed,
        'side':CANONICAL_MILLION_SIDE,
        'cells':CANONICAL_MILLION_CELLS,
        'rounds':CANONICAL_MILLION_ROUNDS,
        'anchorMode':CANONICAL_MILLION_ANCHOR_MODE,
        'finalBlank':list(board.final_blank),
        'physicalLength':decoded.physical_length,
        'grammarNodes':nodes,
        'grammarDepth':depth,
        'grammarDigest':digest,
        'artifactSha256':supplied_digest,
        'boardCellsMaterialized':0,
        'physicalMovesMaterialized':0,
    }


def dumps_solution_artifact(
    artifact:dict[str,Any],
    *,
    pretty:bool=True,
)->str:
    if pretty:
        return json.dumps(
            artifact,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )+'\n'
    return _canonical_json_bytes(artifact).decode('utf-8')+'\n'


def loads_solution_artifact(text:str)->dict[str,Any]:
    payload=json.loads(text)
    if not isinstance(payload,dict):
        raise ValueError('artifact root must be an object')
    return payload


def write_solution_artifact(
    path:Path,
    artifact:dict[str,Any],
)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(
        dumps_solution_artifact(artifact),
        encoding='utf-8',
    )
    temporary.replace(path)


def read_solution_artifact(path:Path)->dict[str,Any]:
    return loads_solution_artifact(path.read_text(encoding='utf-8'))


def main()->None:
    parser=argparse.ArgumentParser(
        description='build or verify a frozen million-side compact solution artifact'
    )
    sub=parser.add_subparsers(dest='command',required=True)

    build=sub.add_parser('build')
    build.add_argument('--seed',type=int,required=True)
    build.add_argument('--output',type=Path,required=True)

    verify=sub.add_parser('verify')
    verify.add_argument('artifact',type=Path)

    args=parser.parse_args()
    if args.command=='build':
        artifact=build_solution_artifact(args.seed)
        write_solution_artifact(args.output,artifact)
        print(json.dumps(verify_solution_artifact(artifact),indent=2))
        return

    artifact=read_solution_artifact(args.artifact)
    print(json.dumps(verify_solution_artifact(artifact),indent=2))


if __name__=='__main__':
    main()
