import unittest
import pandas as pd

from app import (
    BLS_SERIES,
    CPIActual,
    CPIConsensus,
    add_indicators,
    calculate_cpi_actual,
    classify_cpi,
    final_decision,
    technical_stage,
)


class DashboardTests(unittest.TestCase):
    def test_technical_stage(self):
        self.assertEqual(technical_stage(2, "UPTREND")[1], 10.0)
        self.assertEqual(technical_stage(4, "UPTREND")[1], 30.0)
        self.assertEqual(technical_stage(2, "DOWNTREND")[1], 0.0)
        self.assertEqual(technical_stage(4, "DOWNTREND")[1], 15.0)

    def test_final_decision(self):
        result = final_decision(20, 20, 0.5, 0)
        self.assertEqual(result["final_buy_pct"], 10.0)
        self.assertEqual(result["action"], "BUY_ALLOWED")

        delayed = final_decision(20, 20, 1.0, 1)
        self.assertEqual(delayed["final_buy_pct"], 0.0)
        self.assertEqual(delayed["action"], "HOLD_OR_DELAY")

    def test_cpi_actual(self):
        indexes = {
            BLS_SERIES["headline"]: {
                "2025-06": 315.0, "2026-05": 320.0, "2026-06": 321.0,
            },
            BLS_SERIES["core"]: {
                "2025-06": 320.0, "2026-05": 329.0, "2026-06": 330.0,
            },
        }
        actual = calculate_cpi_actual(indexes, "2026-06")
        self.assertEqual(actual.headline_mom, 0.3)
        self.assertEqual(actual.core_yoy, 3.1)

    def test_cpi_classification(self):
        consensus = CPIConsensus(
            "2026-06", "2026-07-14T21:30", "test",
            0.2, 2.7, 0.2, 2.9,
        )
        actual = CPIActual(
            "2026-06", 0.4, 2.8, 0.4, 3.0, "now",
        )
        result = classify_cpi(consensus, actual)
        self.assertEqual(result.classification, "INFLATION_SHOCK")
        self.assertEqual(result.macro_multiplier, 0.0)

    def test_indicators(self):
        index = pd.date_range("2020-01-01", periods=1200, freq="B")
        close = pd.Series(range(1000, 2200), index=index, dtype=float)
        df = add_indicators(pd.DataFrame({"Close": close}), 756, 0.10)
        self.assertIn("Disparity200", df.columns)
        self.assertIn("RSI14", df.columns)
        self.assertIn("OversoldScore", df.columns)
        self.assertTrue(df["OversoldScore"].between(0, 4).all())


if __name__ == "__main__":
    unittest.main()
