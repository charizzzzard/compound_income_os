from __future__ import annotations

import unittest

from src.platform.validation import validate_enum, validate_numeric_range, validate_required_columns


class PlatformValidationTests(unittest.TestCase):
    def test_required_columns_reports_missing_by_zero_based_row_index(self) -> None:
        rows = [{"ticker": "AAA", "score": "90"}, {"ticker": "BBB"}, {"score": "75"}]

        self.assertEqual(validate_required_columns(rows, ["ticker", "score"]), [(1, ["score"]), (2, ["ticker"])])

    def test_required_columns_accepts_blank_existing_values(self) -> None:
        self.assertEqual(validate_required_columns([{"ticker": "", "score": ""}], ["ticker", "score"]), [])

    def test_validate_enum_accepts_only_allowed_values(self) -> None:
        self.assertTrue(validate_enum("REVIEW", ("OK", "REVIEW")))
        self.assertFalse(validate_enum("MISSING_DATA", ("OK", "REVIEW")))

    def test_validate_numeric_range_returns_none_for_bounds_inclusive(self) -> None:
        self.assertIsNone(validate_numeric_range(0, 0, 100))
        self.assertIsNone(validate_numeric_range(100, 0, 100))

    def test_validate_numeric_range_reports_out_of_range_and_rejects_bad_bounds(self) -> None:
        self.assertIn("below", validate_numeric_range(-1, 0, 100) or "")
        self.assertIn("above", validate_numeric_range(101, 0, 100) or "")
        with self.assertRaisesRegex(ValueError, "low"):
            validate_numeric_range(50, 100, 0)


if __name__ == "__main__":
    unittest.main()
