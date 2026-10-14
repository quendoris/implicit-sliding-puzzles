"""Independently replay the exact Hamiltonian blank cycle on small rectangles.

Physical replay is an elementary dense-array swap implementation and does not
import any primitive positional transform. Every pre-position is compared
with the production forward/inverse maps, including a nonzero board offset.
"""
import unittest
from implicit_sliding_puzzles.hamiltonian_rectangle_cycle import HamiltonianRectangleCycle
from implicit_sliding_puzzles.rectangle_cycle_macro import Rectangle
from implicit_sliding_puzzles.recursive_plan_grammar import materialize

STEPS={"U":(-1,0),"D":(1,0),"L":(0,-1),"R":(0,1)}

def independent_physical_mapping(h,w,moves):
    contents=list(range(h*w))
    blank=0
    row=col=0
    for i,ch in enumerate(moves):
        dr,dc=STEPS[ch]
        nr,nc=row+dr,col+dc
        if not(0<=nr<h and 0<=nc<w):
            raise AssertionError(f"illegal step {i}: {ch} from {(row,col)}")
        dst=nr*w+nc
        contents[blank],contents[dst]=contents[dst],contents[blank]
        blank=dst
        row,col=nr,nc
    position_of_original={original:position for position,original in enumerate(contents)}
    if len(position_of_original)!=h*w:
        raise AssertionError("not a permutation")
    return position_of_original, (row,col)

class TestRectangleGeometry(unittest.TestCase):
    def test_rectangle_cycles_against_literal_swaps(self):
        cases=0
        for h in range(2,12):
            for w in range(2,12):
                if h%2 and w%2:
                    continue
                orientations=[]
                if h%2==0:
                    orientations.append("row")
                if w%2==0:
                    orientations.append("column")
                for orientation in orientations:
                    for count in (0,1,2,2*(h*w-1)+1):
                        with self.subTest(h=h,w=w,orientation=orientation,count=count):
                            rect=Rectangle(3,3+h,7,7+w)
                            macro=HamiltonianRectangleCycle(rect,count,preferred_orientation=orientation)
                            moves=materialize(macro.plan,max_moves=100_000)
                            self.assertEqual(len(moves),macro.physical_length)
                            perm,blank=independent_physical_mapping(h,w,moves)
                            self.assertEqual(blank,(0,0))
                            for original,position in perm.items():
                                before=(3+original//w,7+original%w)
                                after=(3+position//w,7+position%w)
                                self.assertEqual(macro.forward(before),after)
                                self.assertEqual(macro.inverse(after),before)
                            for outside in ((2,7),(3,6),(3+h,7+w),(0,0)):
                                self.assertEqual(macro.forward(outside),outside)
                                self.assertEqual(macro.inverse(outside),outside)
                            cases+=1
        self.assertGreater(cases,100)

    def test_invalid_both_odd(self):
        with self.assertRaises(ValueError):
            HamiltonianRectangleCycle(Rectangle(0,3,0,3),1)
