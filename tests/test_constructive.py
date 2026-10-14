"""Independent literal replay and consistency tests for constructed boards."""
import copy
import tempfile
import unittest
from pathlib import Path

from implicit_sliding_puzzles.blank_run import BlankRunTransform, forward_blank_run, inverse_blank_run
from implicit_sliding_puzzles.seeded_legal_hamiltonian_board import SeededLegalHamiltonianBoard
from implicit_sliding_puzzles.recursive_plan_grammar import materialize
from implicit_sliding_puzzles.million_solution_artifact import (
    build_solution_artifact, write_solution_artifact, read_solution_artifact,
    verify_solution_artifact,
)
from implicit_sliding_puzzles.million_solution_query import move_at, moves_range, tile_at, position_of

DIRECTIONS={"U":(-1,0),"D":(1,0),"L":(0,-1),"R":(0,1)}

def canonical(side):
    return [i+1 for i in range(side*side-1)]+[0]

def independent_replay(side, state, moves):
    board=state.copy()
    blank=board.index(0)
    for number, move in enumerate(moves):
        dr,dc=DIRECTIONS[move]
        row,col=divmod(blank,side)
        nr,nc=row+dr,col+dc
        if not (0<=nr<side and 0<=nc<side):
            raise AssertionError(f"illegal move {number}: {move} at {(row,col)}")
        nxt=nr*side+nc
        board[blank],board[nxt]=board[nxt],board[blank]
        blank=nxt
    return board

class TestBlankRun(unittest.TestCase):
    def test_all_directions_against_literal_swaps(self):
        cases=[((0,0),"R",3),((3,3),"L",3),
               ((0,0),"D",3),((3,3),"U",3)]
        for start,direction,count in cases:
            with self.subTest(direction=direction):
                transform=BlankRunTransform(start,direction,count)
                board=list(range(16))
                initial_blank=start[0]*4+start[1]
                board[0],board[initial_blank]=board[initial_blank],board[0]
                expected=independent_replay(4,board,direction*count)
                result=[None]*16
                for before in range(16):
                    target=forward_blank_run(transform,divmod(before,4))
                    after=target[0]*4+target[1]
                    result[after]=board[before]
                    self.assertEqual(inverse_blank_run(transform,target),divmod(before,4))
                self.assertEqual(result,expected)

class TestConstruction(unittest.TestCase):
    def test_small_physical_replay_and_exact_tile_map(self):
        for side,rounds in ((4,5),(8,24),(8,384)):
            with self.subTest(side=side,rounds=rounds):
                board=SeededLegalHamiltonianBoard(side,10363137,rounds=rounds,anchor_mode="wandering")
                forward=materialize(board.scramble_plan,max_moves=2_000_000)
                inverse=materialize(board.solution_plan,max_moves=2_000_000)
                physical=independent_replay(side,canonical(side),forward)
                indexed=[board.value_at(i) for i in range(side*side)]
                self.assertEqual(physical,indexed)
                self.assertEqual(independent_replay(side,physical,inverse),canonical(side))
                for pos,tile in enumerate(indexed):
                    row,col=board.position_of_tile(tile)
                    self.assertEqual(row*side+col,pos)
                self.assertEqual(len(inverse),len(forward))

    def test_million_artifact_roundtrip_and_query(self):
        seed=10363137
        artifact=build_solution_artifact(seed)
        self.assertEqual(verify_solution_artifact(artifact)["status"],"ok")
        self.assertEqual(artifact["profile"]["side"],1000000)
        self.assertEqual(artifact["solution"]["grammarNodes"],5379)
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/"million.solution.json"
            write_solution_artifact(file,artifact)
            self.assertEqual(read_solution_artifact(file),artifact)
            for r,c in ((0,0),(500000,500000),(999999,999999)):
                tile=tile_at(file,r,c)["tile"]
                restored=position_of(file,tile)
                self.assertEqual((restored["row"],restored["col"]),(r,c))
            length=artifact["solution"]["physicalLength"]
            for k in (0,1,length//2,length-1):
                self.assertIn(move_at(file,k)["move"],DIRECTIONS)
            self.assertEqual(len(moves_range(file, length//2,19)["moves"]),19)
        altered=copy.deepcopy(artifact)
        altered["solution"]["physicalLength"]+=1
        with self.assertRaisesRegex(ValueError,"SHA-256 mismatch"):
            verify_solution_artifact(altered)

if __name__=="__main__":
    unittest.main()
