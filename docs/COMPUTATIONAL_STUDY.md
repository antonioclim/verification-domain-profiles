# Computational study

## Design principles

The study evaluates positive verification-domain certificates rather than
frontier generation. Candidate selection is independent of the certificate
weight. Finite weight grids are not used as ground truth. Exact rational replay
is required for every mathematical sign and budget reported as a result.

The frozen protocol is `protocol/COMPUTATIONAL_PROTOCOL.json` with SHA-256
`23b2c592553341be1d219d5cc4584844981e3f9ef0bbde693dbc5311d0e1f632`.

## Correctness corpus

The retained corpus contains 84 cases:

- 60 controlled explicit cases covering 2 to 5 objectives, three domain classes and five seeds
- 12 side-constrained assignment cases
- 12 layered shortest-path cases

The class balance is exact: 28 harmless, 28 repairable and 28 irreparable
cases. The structured cases use sequential epsilon filtering followed by
lexicographic minimisation for candidate selection.

## Exact evidence

- 84/84 class agreements against complete-domain optimisation
- 84/84 minimum-budget agreements
- 196/196 fixed-budget profile agreements
- 84/84 positive-rescaling invariance checks
- complete independent replay of 84 certificates and 196 profile records
- 24/24 resealed semantic mutations rejected

The standalone checker validates finite instances, full-domain feasibility,
restricted-master KKT certificates and irreparability stress witnesses with
standard-library exact rational arithmetic.

## Profile and domain evidence

Across the 24 structured correctness cases, row generation retained a median
of 0.904% of challenger outcomes and a maximum of 5.79%. The maximum number of
structured oracle calls was 15.

The scaling corpus contains 12 cases with implicit domain sizes up to 177,147.
The exact structured method retained only a small fraction of the implicit
catalogue in every case.

## Chebyshev evidence

Thirty-six retained candidates had a finite exact augmentation threshold. The
median ratio between the exact threshold and the former conservative bound was
16.5 and the maximum was 193.08. Equality at the exact threshold produced a
tie and every retained value immediately above a finite threshold invalidated
the certificate.

## Runtime interpretation

The eight small timed correctness cases do not show uniform superiority. The
median ratio of full-domain exact time to structured time was 0.92, so the
complete-domain method was faster in the median small case. The ratio ranged
from 0.26 to 9.94.

A separate numerical full-domain scaling baseline was feasible on eight larger
enumerated cases. There the numerical LP was between 3.30 and 30.50 times
slower than structured row generation, with a median factor of 7.10. This
baseline uses floating-point HiGHS and is retained only for timing context. It
is not used as mathematical ground truth.

## Validation boundary

The repository contains a cross-platform hosted workflow which can be observed after the source is pushed to GitHub. The archive itself validates exact classifications, budgets, profiles and proof-object replay in its recorded environment. Independent physical-machine replication is not claimed. Timing results are descriptive and no portable performance ranking is claimed.

The scale policy is fixed before classification: each objective and active constraint is divided by a declared positive range over the full verification domain. Positive unit transformations update both the raw values and their scales, leaving the normalised instance unchanged. Alternative scale choices define different certificate semantics and must not be mixed within a domain comparison.
