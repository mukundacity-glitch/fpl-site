import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import vortex_model as vm


class VortexModelTests(unittest.TestCase):
    def setUp(self):
        self.matches = [
            {"home": "A", "away": "B", "hy": 2.0, "ay": 0.8, "w": 1.0},
            {"home": "B", "away": "A", "hy": 0.7, "ay": 1.6, "w": 1.0},
            {"home": "A", "away": "C", "hy": 1.8, "ay": 0.9, "w": 1.0},
            {"home": "C", "away": "B", "hy": 1.0, "ay": 1.2, "w": 1.0},
        ]
        self.model = vm.fit(self.matches, ["A", "B", "C"], [])
        self.reference = vm.reference(self.model, ["A", "B", "C"])

    def test_expected_is_positive_and_finite(self):
        for home in (True, False):
            xgf, xga = vm.expected(self.model, "A", "B", home)
            self.assertTrue(math.isfinite(xgf) and xgf > 0)
            self.assertTrue(math.isfinite(xga) and xga > 0)

    def test_fixture_difficulty_range(self):
        result = vm.fixture_difficulty(self.model, self.reference, "A", "B", True)
        for key in ("fdr_att", "fdr_def", "fdr_all"):
            self.assertIn(result[key], {1, 2, 3, 4, 5})

    def test_stronger_attack_is_not_worse_in_sample(self):
        a = vm.expected(self.model, "A", "B", True)[0]
        b = vm.expected(self.model, "B", "A", False)[0]
        self.assertGreater(a, b)


if __name__ == "__main__":
    unittest.main()
