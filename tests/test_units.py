"""Regression checks for converting retained daily history without drift."""
import copy
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).parents[1] / "custom_components/portsmouth_water/data.py"
spec = importlib.util.spec_from_file_location("water_data", SOURCE)
data = importlib.util.module_from_spec(spec)
spec.loader.exec_module(data)


class UnitConversionTests(unittest.TestCase):
    def setUp(self):
        self.history = {
            "1": {"end": "2026-01-02T00:00:00+00:00", "value": "0.624"},
            "2": {"end": "2026-01-03T00:00:00+00:00", "value": "0.001"},
        }

    def test_daily_values_and_totals(self):
        litres = data.cumulative(self.history, "L")
        cubic_metres = data.cumulative(self.history, "m³")
        self.assertEqual(litres[1]["state"], 624)
        self.assertEqual(cubic_metres[1]["state"], 0.624)
        self.assertEqual(litres[-1]["sum"], 625)
        self.assertEqual(cubic_metres[-1]["sum"], 0.625)
        self.assertEqual(litres[-1]["state"], 1)
        self.assertEqual(cubic_metres[-1]["state"], 0.001)

    def test_switching_preserves_canonical_records_and_dates(self):
        original = copy.deepcopy(self.history)
        for _ in range(10):
            litres = data.cumulative(self.history, "L")
            cubic_metres = data.cumulative(self.history, "m³")
            self.assertEqual(litres[-1]["sum"], 625)
            self.assertEqual(cubic_metres[-1]["sum"], 0.625)
            self.assertEqual([r["start"] for r in litres], [r["start"] for r in cubic_metres])
        self.assertEqual(self.history, original)

    def test_supplier_correction_rebuilds_both_units(self):
        self.history["1"]["value"] = "0.600"
        self.assertEqual(data.cumulative(self.history, "L")[-1]["sum"], 601)
        self.assertEqual(data.cumulative(self.history, "m³")[-1]["sum"], 0.601)

    def test_empty_history_and_invalid_unit(self):
        self.assertEqual(data.cumulative({}, "L"), [])
        with self.assertRaises(ValueError):
            data.usage_value("1", "gal")


if __name__ == "__main__":
    unittest.main()
