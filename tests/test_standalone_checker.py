from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_checker():
    spec = importlib.util.spec_from_file_location("standalone_checker_test", ROOT / "checker/verify_profile_object.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StandaloneCheckerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.checker = load_checker()

    def load(self, relative):
        return json.loads((ROOT / relative).read_text(encoding="utf-8"))

    def verify_certificate(self, case_id):
        return self.checker.verify_minimum_budget(
            self.load(f"results/instances/{case_id}.json"),
            self.load(f"results/certificates/{case_id}.json"),
        )

    def test_harmless_certificate(self):
        self.assertEqual(self.verify_certificate("explicit-p2-harmless-s101")["classification"], "harmless")

    def test_repairable_certificate(self):
        self.assertEqual(self.verify_certificate("assignment-n6-p2-s12")["classification"], "repairable")

    def test_irreparable_certificate(self):
        self.assertEqual(self.verify_certificate("path-w3-l5-p2-s1")["classification"], "irreparable")

    def test_profile_record(self):
        case_id = "explicit-p2-repairable-s101"
        report = self.checker.verify_profile(
            self.load(f"results/instances/{case_id}.json"),
            self.load(f"results/profiles/{case_id}-b0.json"),
        )
        self.assertEqual(report["status"], "VERIFIED")

    def test_mutated_budget_is_rejected(self):
        case_id = "explicit-p2-repairable-s101"
        instance = self.load(f"results/instances/{case_id}.json")
        certificate = self.load(f"results/certificates/{case_id}.json")
        certificate["result"]["budget"] = "3/2"
        with self.assertRaises(self.checker.Rejected):
            self.checker.verify_minimum_budget(instance, certificate)

    def test_noncanonical_rational_is_rejected(self):
        case_id = "explicit-p2-repairable-s101"
        instance = self.load(f"results/instances/{case_id}.json")
        certificate = self.load(f"results/certificates/{case_id}.json")
        certificate["result"]["parameters"]["weights"][0] = "2/4"
        with self.assertRaises(self.checker.Rejected):
            self.checker.verify_minimum_budget(instance, certificate)


if __name__ == "__main__":
    unittest.main()
