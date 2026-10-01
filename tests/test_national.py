"""Guard Q40 ratings and valid denominators without individual survey inputs."""
import unittest

import pandas as pd

from pvs.national import q40_top2


class Q40RatingTests(unittest.TestCase):
    def test_thai_ratings_use_only_evaluable_responses_in_denominator(self):
        values = pd.Series(["แย่", "พอใช้", "ดี", "ดีมาก", "ดีเยี่ยม",
                            "ไม่สามารถประเมินได้", None], name="maternal")
        before = values.copy(deep=True)
        result = q40_top2(values)
        expected = pd.Series([False, False, False, True, True, pd.NA, pd.NA],
                             dtype="boolean", name="maternal")
        pd.testing.assert_series_equal(result, expected)
        self.assertEqual(result.notna().sum(), 5)
        self.assertEqual(result.sum(), 2)
        self.assertEqual(result.mean(), 0.4)
        pd.testing.assert_series_equal(values, before)

    def test_unknown_response_does_not_silently_change_denominator(self):
        for label in ("3. ดีมาก", "ไม่ทราบ", "unexpected"):
            with self.subTest(label=label), self.assertRaisesRegex(ValueError, "Unrecognised Q40"):
                q40_top2(pd.Series(["ดีมาก", label]))

    def test_no_evaluable_responses_does_not_produce_zero_percent(self):
        result = q40_top2(pd.Series(["ไม่สามารถประเมินได้", None]))
        self.assertEqual(result.notna().sum(), 0)
        self.assertTrue(pd.isna(result.mean()))


if __name__ == "__main__":
    unittest.main()
