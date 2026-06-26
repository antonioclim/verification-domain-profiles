import unittest

from mmor_certificates.instances import random_assignment_data, random_layered_path_data
from mmor_certificates.oracles import AssignmentOracle, ExplicitOracle, LayeredPathOracle
from mmor_certificates.profile import (
    classify_minimum_budget,
    minimum_budget_row_generation,
)


class StructuredOracleTests(unittest.TestCase):
    def test_assignment_agrees_with_enumeration(self):
        for p, seed in ((2, 12), (3, 5), (4, 13), (5, 1)):
            data = random_assignment_data(6, p, seed)
            finite = data.to_finite_instance()
            explicit = minimum_budget_row_generation(ExplicitOracle(finite))
            structured = minimum_budget_row_generation(AssignmentOracle(data))
            self.assertEqual(classify_minimum_budget(explicit), classify_minimum_budget(structured))
            self.assertEqual(explicit.budget, structured.budget)

    def test_layered_path_agrees_with_enumeration(self):
        for p, seed in ((2, 2), (3, 9), (4, 5), (5, 5)):
            data = random_layered_path_data(3, 5, p, seed)
            finite = data.to_finite_instance()
            explicit = minimum_budget_row_generation(ExplicitOracle(finite))
            structured = minimum_budget_row_generation(LayeredPathOracle(data))
            self.assertEqual(classify_minimum_budget(explicit), classify_minimum_budget(structured))
            self.assertEqual(explicit.budget, structured.budget)


if __name__ == "__main__":
    unittest.main()
