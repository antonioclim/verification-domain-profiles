from fractions import Fraction as Q
import unittest

from mmor_certificates.chebyshev import tailored_interval, verify_candidate
from mmor_certificates.instances import explicit_profile_instance
from mmor_certificates.oracles import ExplicitOracle
from mmor_certificates.profile import (
    classify_minimum_budget,
    fixed_budget_row_generation,
    full_domain_minimum_budget,
    full_domain_profile,
    minimum_budget_row_generation,
)


class ExactCoreTests(unittest.TestCase):
    def test_controlled_trichotomy(self):
        for p in range(2, 6):
            for class_name in ("harmless", "repairable", "irreparable"):
                instance = explicit_profile_instance(p, class_name, 101)
                full = full_domain_minimum_budget(instance)
                row = minimum_budget_row_generation(ExplicitOracle(instance))
                self.assertEqual(classify_minimum_budget(full), class_name)
                self.assertEqual(classify_minimum_budget(row), class_name)
                self.assertEqual(full.budget, row.budget)

    def test_profile_row_generation(self):
        instance = explicit_profile_instance(4, "repairable", 102)
        minimum = minimum_budget_row_generation(ExplicitOracle(instance))
        self.assertIsNotNone(minimum.budget)
        for budget in (Q(0), minimum.budget / 2, minimum.budget, minimum.budget * 2):
            self.assertEqual(
                full_domain_profile(instance, budget).value,
                fixed_budget_row_generation(ExplicitOracle(instance), budget).value,
            )

    def test_scale_invariance(self):
        instance = explicit_profile_instance(3, "repairable", 103)
        original = minimum_budget_row_generation(ExplicitOracle(instance))
        from mmor_certificates.model import Alternative, FiniteInstance
        scaled = FiniteInstance(
            identifier="scaled",
            candidate_id=instance.candidate_id,
            alternatives=tuple(
                Alternative(
                    alt.identifier,
                    tuple(v * factor for v, factor in zip(alt.objectives, (2, 5, 7))),
                    tuple(v * 11 for v in alt.constraints),
                    alt.decision,
                )
                for alt in instance.alternatives
            ),
            objective_scales=tuple(v * factor for v, factor in zip(instance.objective_scales, (2, 5, 7))),
            constraint_scales=tuple(v * 11 for v in instance.constraint_scales),
        )
        transformed = minimum_budget_row_generation(ExplicitOracle(scaled))
        self.assertEqual(original.budget, transformed.budget)
        self.assertEqual(classify_minimum_budget(original), classify_minimum_budget(transformed))

    def test_exact_chebyshev_interval(self):
        outcomes = [(0, 7), (5, 4), (8, 0)]
        interval = tailored_interval(outcomes, 1)
        self.assertIsNotNone(interval.upper)
        ok, gap = verify_candidate(outcomes, 1, interval, interval.upper / 2)
        self.assertTrue(ok)
        self.assertGreater(gap, 0)
        ok_at, gap_at = verify_candidate(outcomes, 1, interval, interval.upper)
        self.assertTrue(ok_at)
        self.assertEqual(gap_at, 0)
        ok_above, _ = verify_candidate(outcomes, 1, interval, interval.upper + Q(1, 100))
        self.assertFalse(ok_above)


if __name__ == "__main__":
    unittest.main()
