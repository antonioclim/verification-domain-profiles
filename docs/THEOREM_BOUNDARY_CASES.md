# Theorem boundary cases and qualifications

## Scope

The following boundary cases and qualifications are part of the formal contract.

## 1. Empty and singleton domains

The max-min profile is undefined as an ordinary finite margin when there is no challenger. The theory therefore separates `V={x0}` and assigns the convention `Gamma_V(B)=+infinity`. No LP, duality or breakpoint theorem is applied to that case.

**Status:** resolved.

## 2. No active constraints

When the active set is empty, `nu` and `h` are empty, `H(q)=0` and the profile is independent of `B`. The theory reduces to weighted-sum supportability and does not create fictitious multiplier effects.

**Status:** resolved.

## 3. Strict versus non-strict positive certificates

`Gamma_V(B)>=0` yields a non-negative weighted-sum certificate. It does not imply Pareto efficiency unless the attached `lambda` is strictly positive or efficiency is established independently. A positive margin yields uniqueness for the attached scalarisation but does not force every objective weight to be positive.

**Qualification:** the article must preserve this distinction.

## 4. Sign of active-constraint terms

For feasible alternatives, active-constraint differences are non-positive. This is why positive multipliers cannot improve the profile on the feasible domain. The proof uses the inequality in the correct direction.

**Status:** resolved.

## 5. Budget monotonicity versus harmful multipliers

A particular positive multiplier vector may reduce margins on feasible alternatives. The profile is nevertheless non-decreasing because the budget is an upper bound and zero additional multiplier use remains feasible.

**Status:** resolved.

## 6. Concavity and continuity at zero

Concavity is proved by combining feasible certificate parameters, not by an invalid pointwise-max argument. A direct Lipschitz bound establishes right continuity at zero and continuity on the full non-negative budget axis.

**Status:** resolved.

## 7. Dual sign conventions

The exact primal and dual LPs were derived with the budget dual variable constrained non-negative. Exact vertex enumeration matched all 400 tested primal-dual values.

**Status:** resolved.

## 8. Irreparability converse

The converse is not inferred from asymptotics. It uses the finite lower-envelope representation of the rational dual polyhedron. If no zero-slope negative line exists, a finite budget makes every relevant line non-negative.

**Status:** resolved.

## 9. Zero denominator in the budget ratio

Distributions with `H(q)=0` are split explicitly. If one has `D(q)<0`, the domain is irreparable. Otherwise such distributions impose no finite ratio constraint. Formula (16) ranges only over `H(q)>0`.

**Status:** resolved.

## 10. Attainment of the minimum budget

The profile is continuous. A finite infimum budget is therefore successful and equals the optimum of the explicit minimal-budget LP.

**Status:** resolved.

## 11. Rationality and bit length

The rationality result is restricted to explicit rational finite data. The determinant bound is stated after integer scaling and does not claim strong polynomiality or a compact decision encoding for implicit models.

**Status:** resolved with a required independent line-by-line proof check before article freeze.

## 12. Empty max-margin master

The empty restricted profile master is unbounded in the margin variable. The fixed-budget row-generation procedure is therefore seeded by an oracle call before the first master solve.

**Qualification:** the seeded formulation is normative.

## 13. Minimal-budget restricted infeasibility

The minimal-budget restriction may become infeasible. Infeasibility is meaningful because the programme has no free margin variable. It implies infeasibility of the full problem. This is distinct from the original max-margin master, which could not be infeasible.

**Status:** resolved.

## 14. Repeated challengers

A challenger returned with strictly negative violation cannot already be in the restricted pool because all pooled rows are feasible for the current restricted solution. Exact tests confirmed finite termination.

**Status:** resolved.

## 15. Numerical discovery versus mathematical acceptance

Numerical LP values and solver tolerances are not accepted as final mathematical signs. Rational reconstruction and exact full-domain separation are mandatory.

**Qualification:** mandatory for every retained computational result.

## 16. Chebyshev lower and upper endpoints

The general admissible interval treats positive, negative and zero sum differences separately. Tailored complete weights imply positive base gaps, making the strict lower endpoint zero. A finite upper endpoint is a non-strict tie and any value above it invalidates the certificate.

**Status:** resolved and checked on 1000 exact finite-image cases.

## 17. Conservative baseline bound

The former `delta/Delta0` condition is not called exact. It is retained only as a sufficient corollary below the exact upper threshold.

**Status:** resolved.

## 18. Perturbed feasibility

The profile perturbation theorem concerns fixed normalised differences. Pareto conclusions require the feasible set and active set to remain unchanged. No robust-feasibility claim is made.

**Status:** resolved.

## 19. Scope boundary

The theory concerns positive certificate strength under verification-domain enlargement and multiplier budgets. It excludes pure weighted-sum negative integral certificates, coefficient bounds for such objects and candidate-level unsupportedness complexity.

**Qualification:** declared scope boundary.

## Public claim boundary

The public claims exclude output-sensitive domain-atlas enumeration, polynomial oracle-call complexity, universal runtime superiority and any result reserved for negative unsupportedness certificates.
