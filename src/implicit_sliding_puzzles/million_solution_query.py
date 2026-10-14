#!/usr/bin/env python3
"""Query a frozen million-side puzzle/solution artifact without expansion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .canonical_million_legal_board import build_canonical_million_board
from .million_solution_artifact import (
    read_solution_artifact,
    verify_solution_artifact,
)
from .recursive_plan_grammar import plan_from_obj


MAX_RANGE_MOVES=100_000


def load_verified(path:Path):
    artifact=read_solution_artifact(path)
    verification=verify_solution_artifact(artifact)
    board=build_canonical_million_board(int(artifact['seed']))
    solution=plan_from_obj(artifact['solution']['grammar'])
    return artifact,verification,board,solution


def info(path:Path)->dict[str,object]:
    artifact,verified,_board,_solution=load_verified(path)
    return {
        **verified,
        'artifactBytes':path.stat().st_size,
        'finalBlank':artifact['finalBlank'],
    }


def tile_at(path:Path,row:int,col:int)->dict[str,object]:
    _artifact,verified,board,_solution=load_verified(path)
    value=board.tile_at(row,col)
    return {
        'status':'ok',
        'artifactSha256':verified['artifactSha256'],
        'row':row,
        'col':col,
        'position':row*board.side+col,
        'tile':value,
    }


def position_of(path:Path,tile:int)->dict[str,object]:
    _artifact,verified,board,_solution=load_verified(path)
    row,col=board.position_of_tile(tile)
    return {
        'status':'ok',
        'artifactSha256':verified['artifactSha256'],
        'tile':tile,
        'row':row,
        'col':col,
        'position':row*board.side+col,
    }


def move_at(path:Path,index:int)->dict[str,object]:
    _artifact,verified,_board,solution=load_verified(path)
    if not 0<=index<solution.physical_length:
        raise IndexError(index)
    return {
        'status':'ok',
        'artifactSha256':verified['artifactSha256'],
        'index':index,
        'move':solution.move_at(index),
        'physicalLength':solution.physical_length,
    }


def moves_range(
    path:Path,
    start:int,
    count:int,
)->dict[str,object]:
    if count<0:
        raise ValueError('count must be nonnegative')
    if count>MAX_RANGE_MOVES:
        raise ValueError(
            f'count exceeds safety guard {MAX_RANGE_MOVES}'
        )
    _artifact,verified,_board,solution=load_verified(path)
    end=start+count
    if not (0<=start<=end<=solution.physical_length):
        raise IndexError((start,count))
    moves=''.join(
        solution.move_at(index)
        for index in range(start,end)
    )
    return {
        'status':'ok',
        'artifactSha256':verified['artifactSha256'],
        'start':start,
        'count':count,
        'endExclusive':end,
        'moves':moves,
        'physicalLength':solution.physical_length,
    }


def main()->None:
    parser=argparse.ArgumentParser(
        description='query an exact compact million-side solution artifact'
    )
    sub=parser.add_subparsers(dest='command',required=True)

    p=sub.add_parser('info')
    p.add_argument('artifact',type=Path)

    p=sub.add_parser('tile-at')
    p.add_argument('artifact',type=Path)
    p.add_argument('row',type=int)
    p.add_argument('col',type=int)

    p=sub.add_parser('position-of')
    p.add_argument('artifact',type=Path)
    p.add_argument('tile',type=int)

    p=sub.add_parser('move-at')
    p.add_argument('artifact',type=Path)
    p.add_argument('index',type=int)

    p=sub.add_parser('moves-range')
    p.add_argument('artifact',type=Path)
    p.add_argument('start',type=int)
    p.add_argument('count',type=int)

    args=parser.parse_args()
    if args.command=='info':
        result=info(args.artifact)
    elif args.command=='tile-at':
        result=tile_at(args.artifact,args.row,args.col)
    elif args.command=='position-of':
        result=position_of(args.artifact,args.tile)
    elif args.command=='move-at':
        result=move_at(args.artifact,args.index)
    else:
        result=moves_range(args.artifact,args.start,args.count)
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    main()
