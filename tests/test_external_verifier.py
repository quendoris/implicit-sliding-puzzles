"""Independent subprocess checks: verifier does not import the generator."""
from __future__ import annotations
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from implicit_sliding_puzzles.million_solution_artifact import build_solution_artifact,write_solution_artifact

ROOT=Path(__file__).resolve().parents[1]
VERIFIER=ROOT/"tools"/"verify_artifact.py"

class TestIndependentVerifier(unittest.TestCase):
    def test_verified_json_and_pinned_hash(self):
        artifact=build_solution_artifact(10363137)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"million.json"
            write_solution_artifact(path,artifact)
            command=[sys.executable,str(VERIFIER),str(path),
                     "--expected-sha256",artifact["artifactSha256"],
                     "--indices","0,1,123456789"]
            proc=subprocess.run(command,check=True,capture_output=True,text=True)
            result=json.loads(proc.stdout)
            self.assertEqual(result["status"],"ok")
            self.assertEqual(result["physicalLength"],artifact["solution"]["physicalLength"])
            self.assertEqual(result["grammarNodes"],5379)
            command[4]="0"*64
            bad=subprocess.run(command,capture_output=True,text=True)
            self.assertNotEqual(bad.returncode,0)
            self.assertIn("pinned SHA-256 mismatch",bad.stderr)
