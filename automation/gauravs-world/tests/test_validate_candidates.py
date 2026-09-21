#!/usr/bin/env python3
"""Regression tests for validate_candidates.py; stdlib only, no network or blog writes."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_candidates.py"


class CandidateValidationTests(unittest.TestCase):
    def run_validator(self, payload):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "automation/gauravs-world/output"
            root.mkdir(parents=True)
            (root / "news-candidates.json").write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
            copied = Path(tmp) / "validate_candidates.py"
            shutil.copy2(SCRIPT, copied)
            proc = subprocess.run(
                ["python", str(copied)], cwd=tmp, text=True,
                capture_output=True, check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            result = json.loads((root / "candidate-validation.json").read_text(encoding="utf-8"))
            return result, proc.stdout

    def test_accepts_valid_candidate_and_marks_review_only(self):
        result, output = self.run_validator({"candidates": [{"title": "AI grid security", "url": "https://example.com/story"}]})
        self.assertEqual(result["accepted_count"], 1)
        self.assertEqual(result["rejected_count"], 0)
        self.assertTrue(result["draft_only"])
        self.assertFalse(result["publication_performed"])
        self.assertFalse(result["blog_api_called"])
        self.assertIn("no publishing", output)

    def test_rejects_missing_title_and_bad_scheme(self):
        result, _ = self.run_validator({"candidates": [{"title": "", "url": "javascript:alert(1)"}]})
        self.assertEqual(result["accepted_count"], 0)
        self.assertEqual(result["rejected"][0]["reasons"], ["missing_title", "invalid_url"])

    def test_detects_duplicate_url_and_normalized_title(self):
        result, _ = self.run_validator({"candidates": [
            {"title": "AI: Grid Security", "url": "https://example.com/story?utm=x"},
            {"title": "AI Grid Security!", "url": "https://example.com/story/"},
        ]})
        self.assertEqual(result["accepted_count"], 1)
        self.assertEqual(result["rejected_count"], 1)
        self.assertIn("duplicate_url", result["rejected"][0]["reasons"])
        self.assertIn("duplicate_title", result["rejected"][0]["reasons"])

    def test_empty_candidates_has_safe_status(self):
        result, _ = self.run_validator({"candidates": []})
        self.assertEqual(result["status"], "no_valid_candidates")
        self.assertEqual(result["accepted_count"], 0)
        self.assertFalse(result["publication_performed"])


if __name__ == "__main__":
    unittest.main()
