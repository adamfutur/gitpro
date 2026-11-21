"""Regression tests for explainable PR review priority (stdlib only)."""
import unittest
from services.pr_risk import analyze_pr_risk


class RiskRadarTests(unittest.TestCase):
    def test_empty_change_is_low_and_complete(self):
        risk = analyze_pr_risk([])
        self.assertEqual(risk["score"], 0)
        self.assertTrue(risk["coverage"]["complete"])

    def test_sensitive_change_ranks_above_test(self):
        risk = analyze_pr_risk([
            {"filename": "tests/test_auth.py", "additions": 150, "deletions": 0, "patch": "x"},
            {"filename": "backend/auth/login.py", "additions": 150, "deletions": 5, "patch": "x"},
        ])
        self.assertEqual(risk["files"][0]["path"], "backend/auth/login.py")
        self.assertEqual(risk["level"], "high")
        self.assertTrue(risk["test_files_changed"])

    def test_reports_ai_coverage_limit_and_truncation(self):
        files = [
            {"filename": f"src/file_{i}.py", "additions": 2, "patch": "abcde"}
            for i in range(24)
        ]
        risk = analyze_pr_risk(files, reviewed_file_limit=20, patch_char_limit=4)
        self.assertEqual(risk["coverage"]["files_not_selected"], 4)
        self.assertEqual(risk["coverage"]["files_with_truncated_patches"], 20)
        self.assertFalse(risk["coverage"]["complete"])

    def test_missing_patches_not_counted_as_covered(self):
        risk = analyze_pr_risk([{"filename": "src/a.py", "additions": 2}])
        self.assertEqual(risk["coverage"]["files_with_patches"], 0)
        self.assertFalse(risk["coverage"]["complete"])

    def test_review_checklist_suggests_tests_without_claiming_failure(self):
        risk = analyze_pr_risk([{"filename": "src/a.py", "additions": 3, "patch": "x"}])
        self.assertIn("No test files changed", " ".join(risk["review_checklist"]))
        self.assertFalse(risk["test_files_changed"])

    def test_score_is_bounded_and_inputs_are_not_mutated(self):
        files = [{"filename": ".env.production", "additions": 1000000, "deletions": 5, "patch": "x"}]
        original = [dict(f) for f in files]
        risk = analyze_pr_risk(files)
        self.assertLessEqual(risk["score"], 100)
        self.assertGreaterEqual(risk["score"], 0)
        self.assertEqual(files, original)


if __name__ == "__main__":
    unittest.main()
