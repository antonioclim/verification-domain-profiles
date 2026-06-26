from fractions import Fraction as Q
import unittest

from mmor_certificates.exact_lp import solve_exact_lp


class ExactLPTests(unittest.TestCase):
    def test_minimum_with_exact_kkt(self):
        result = solve_exact_lp(
            [Q(1), Q(1)],
            [([Q(1), Q(1)], Q(1)), ([Q(1), Q(0)], Q(0)), ([Q(0), Q(1)], Q(0))],
            [],
        )
        self.assertTrue(result.optimal)
        self.assertEqual(result.objective, Q(1))
        self.assertEqual(sum(result.point), Q(1))

    def test_maximum_with_equality(self):
        result = solve_exact_lp(
            [Q(1), Q(0)],
            [([Q(1), Q(0)], Q(0)), ([Q(0), Q(1)], Q(0))],
            [([Q(1), Q(1)], Q(1))],
            maximise=True,
        )
        self.assertTrue(result.optimal)
        self.assertEqual(result.objective, Q(1))
        self.assertEqual(result.point, (Q(1), Q(0)))

    def test_fractional_vertex(self):
        result = solve_exact_lp(
            [Q(1), Q(0)],
            [([Q(2), Q(1)], Q(1)), ([Q(1), Q(0)], Q(0)), ([Q(0), Q(1)], Q(0))],
            [([Q(0), Q(1)], Q(0))],
        )
        self.assertTrue(result.optimal)
        self.assertEqual(result.point[0], Q(1, 2))
        self.assertEqual(result.objective, Q(1, 2))

    def test_infeasible_status(self):
        result = solve_exact_lp(
            [Q(1)],
            [([Q(1)], Q(1)), ([-Q(1)], Q(0))],
            [],
        )
        self.assertTrue(result.status.startswith("INFEASIBLE"))

    def test_unbounded_status(self):
        result = solve_exact_lp([Q(-1)], [([Q(1)], Q(0))], [])
        self.assertTrue(result.status.startswith("UNBOUNDED"))


if __name__ == "__main__":
    unittest.main()
