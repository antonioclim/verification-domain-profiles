# Proof-object contract

## Minimum-budget certificate

A certificate binds one finite verification-domain instance by SHA-256 and
contains exactly one of the following outcomes.

### Harmless or repairable domain

The object records:

- exact simplex objective weights
- exact non-negative normalised multipliers
- exact total multiplier budget
- exact global separator margin
- the restricted challenger identifiers
- an exact KKT certificate proving the restricted master optimum
- the final full-domain verification data

The standalone checker evaluates every alternative in the retained finite
instance. Global feasibility plus the restricted KKT lower bound proves the
minimum budget exactly. When the reported budget is zero, multiplier
non-negativity supplies the global lower bound directly.

### Irreparable domain

The object records a probability distribution over retained challengers and a
strict positive depth. The checker confirms that the averaged normalised
objective differences are at most minus the depth in every objective and that
the averaged active-constraint differences are non-positive. This excludes
every finite multiplier budget.

## Fixed-budget profile record

A profile record contains the declared budget, exact profile value, exact
parameters, retained challenger identifiers and an exact KKT certificate for
the restricted max-margin master. Full-domain evaluation confirms that the
reported parameters achieve the recorded profile value globally.

## Trust boundary

The retained finite instances are explicit and all 280 certificate/profile
objects are fully checkable without an optimiser. Structured assignment and
layered-path oracle proofs are retained for provenance but are not trusted by
the standalone replay: the checker evaluates the complete finite instance.

The self-contained replay does not prove that a structured oracle will scale
to arbitrary larger instances. That claim is evaluated separately by the
algorithmic tests and scaling study.
