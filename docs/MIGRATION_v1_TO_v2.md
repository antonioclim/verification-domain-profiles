# Migration from 1.0.0 to 2.0.0

Version 2.0.0 is a major scientific and software reconstruction rather than an API-compatible patch.

## Conceptual change

Version 1.0.0 checked several candidate-level certificate families over finite catalogues. Version 2.0.0 centres on the scale-normalised verification-domain profile `Gamma_V(B)`, exact minimum multiplier budgets and the harmless/repairable/irreparable domain trichotomy.

## Interface change

The package name is `mmor-verification-profiles` and the Python package is `mmor_certificates`. Version 1 imports under `cert_pareto` are not preserved. Proof objects use new schemas and cannot be interpreted by either version's other checker.

## Evidence change

All retained instances, profile records, minimum-budget certificates, raw results and figures in version 2 were regenerated under the frozen version-2 protocol. They do not replace the evidence needed to reproduce version 1.

## Archival rule

Keep version 1.0.0 tags and archival records unchanged for provenance. Cite the exact version used. New work based on verification-domain profiles should use version 2.0.0 or later.
