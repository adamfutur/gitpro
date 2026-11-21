"""Review verdicts must never silently pass malformed model responses."""
import unittest
from services.review_verdict import extract_verdict


class VerdictSafetyTests(unittest.TestCase):
    def test_missing_block_is_inconclusive(self):
        _, result = extract_verdict("Nice changes.")
        self.assertEqual(result["status"], "inconclusive")

    def test_invalid_json_is_inconclusive(self):
        _, result = extract_verdict("Review\n```gitcat-verdict\n{bad json}\n```")
        self.assertEqual(result["status"], "inconclusive")

    def test_missing_reason_is_inconclusive(self):
        _, result = extract_verdict('```gitcat-verdict\n{"status": "pass"}\n```')
        self.assertEqual(result["status"], "inconclusive")

    def test_valid_pass_and_fail(self):
        for status in ("pass", "fail"):
            body, verdict = extract_verdict(
                'Review\n```gitcat-verdict\n{"status": "' + status
                + '", "reason": "Reviewed all changes"}\n```'
            )
            self.assertEqual(verdict["status"], status)
            self.assertEqual(body, "Review")

    def test_non_object_is_inconclusive(self):
        _, result = extract_verdict('```gitcat-verdict\n[]\n```')
        self.assertEqual(result["status"], "inconclusive")


if __name__ == "__main__":
    unittest.main()
