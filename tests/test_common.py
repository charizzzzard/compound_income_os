from __future__ import annotations

import unittest

from src.common import to_float


class CommonParsingTests(unittest.TestCase):
    def test_to_float_handles_us_and_german_formats(self) -> None:
        self.assertEqual(to_float("1234.56"), 1234.56)
        self.assertEqual(to_float("1,234.56"), 1234.56)
        self.assertEqual(to_float("1234,56"), 1234.56)
        self.assertEqual(to_float("1.234,56"), 1234.56)
        self.assertEqual(to_float("12%"), 12.0)
        self.assertEqual(to_float("0,3453"), 0.3453)


if __name__ == "__main__":
    unittest.main()
