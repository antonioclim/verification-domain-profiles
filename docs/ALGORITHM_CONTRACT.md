# Exact algorithm contract

## Minimal-budget generation

The authoritative optimisation problem is

\[
\min\{\mathbf 1^\top\nu:\lambda\in\Delta_p,\nu\ge0,
\lambda^\top d(x)+\nu^\top h(x)\ge0\ \forall x\in V\setminus\{x^0\}\}.
\]

The implementation may solve restricted masters numerically for discovery. A publishable output must be rationally reconstructed and rechecked against an exact global separator.

### Required statuses

- `CERTIFIED_MINIMUM_BUDGET`: exact full-domain separator is non-negative and the returned restricted optimum is globally feasible.
- `IRREPARABLE_DOMAIN`: an exact restricted LP alternative or exact dual obstruction is attached.
- `UNRESOLVED_NUMERICALLY`: rational reconstruction or exact separation failed. This status is not a mathematical conclusion.

## Fixed-budget profile

The empty max-margin master is unbounded. It must be seeded by one exact oracle call. The returned profile value is accepted only when the full-domain oracle value is no smaller than the restricted margin.

## Exact object fields

Every certificate record must include:

- candidate decision identifier and exact outcome
- verification-domain identifier and digest
- active-set identifier
- positive objective scales and active-constraint scales
- reduced rational objective weights
- reduced rational normalised multipliers
- exact total multiplier budget
- exact separator value
- exact profile margin
- strict or non-strict status
- oracle adapter and proof status
- software and schema versions

## Prohibited shortcuts

- finite weight grids as supportability ground truth
- floating-point signs without exact replay
- unnormalised multiplier-budget comparisons
- `master infeasible` for the max-margin formulation
- a cut pool described as a portable negative proof without its exact LP alternative
- deletion of failed cases after observing results
