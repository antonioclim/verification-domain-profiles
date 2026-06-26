# Related-work and benchmark boundaries

## Scope of the contribution

The release supports a candidate-level theory of positive scalarisation
certificates over declared finite verification domains. Its central objects are
the normalised profile `Gamma_V(B)`, the minimum successful multiplier budget,
the harmless/repairable/irreparable trichotomy, the finite minimax stress dual
and exact augmented-Chebyshev parameter intervals.

The release does not claim priority for weighted-sum scalarisation, Lagrangian
relaxation, finite minimax, Caratheodory support reduction, augmented
Chebyshev scalarisation, parametric linear programming or row generation as
general techniques. These are used as established ingredients.

## Combined claims examined by the project

The project examines the following combined claims:

- a scale-invariant positive-certificate profile indexed jointly by the
  verification domain and a normalised active-multiplier budget
- an exact sparse-stress dual representation of that profile
- an exact harmless/repairable/irreparable classification of verification
  domains
- an exact worst-stress formula for the minimum successful multiplier budget
- exact row-generation procedures for minimum-budget and fixed-budget profile
  computation
- an exact admissible interval for the augmentation parameter of a fixed
  finite augmented-Chebyshev certificate

A targeted search of the published and publicly available literature through 25 June 2026 did not identify the same combined profile, dual and domain-trichotomy construction. This statement is a documented search result rather than an exhaustive priority certification.

## Boundary with frontier algorithms

The retained algorithms classify and certify one selected candidate. They do
not enumerate the Pareto frontier or the Edgeworth-Pareto hull. Objective-space
and outer-approximation methods are therefore methodological comparators rather
than interchangeable implementations.

The computational evidence establishes exact agreement against complete-domain
optimisation and evaluates row economy. It does not establish a universal
runtime advantage over frontier enumeration, full-domain linear programming or
mixed-integer solvers.

## Boundary with weighted-sum unsupportedness certificates

This project concerns positive certificates obtained from objective weights and
normalised active-constraint multipliers. It does not claim sparse integral
negative certificates for weighted-sum unsupportedness, coefficient bounds for
such certificates or candidate-level unsupportedness complexity. Those results
belong to a distinct research contribution and software line.

## Benchmark interpretation

- Complete-domain exact optimisation is the mathematical baseline for the
  retained finite corpus.
- Structured assignment and layered-path separation are tested against complete
  enumeration on every correctness case where both are available.
- Floating-point HiGHS is used only as a descriptive scaling-time baseline and
  is never used as mathematical ground truth.
- Small-instance timings do not show uniform superiority and are reported as
  such.
- Hosted cross-platform execution becomes observable after the repository update. Independent physical-machine replication is not claimed by this archive.
