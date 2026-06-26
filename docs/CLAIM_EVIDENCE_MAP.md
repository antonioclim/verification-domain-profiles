# Claim-to-evidence map

| Result | Normative implementation or evidence | Status | Qualification |
|---|---|---|---|
| Soundness and strictness of the profile | `docs/MATHEMATICAL_CONTRACT.md`; exact finite replay | PASS | Positive weights are required for the Pareto-efficiency conclusion |
| Positive-rescaling invariance | 84 independently rescaled cases; `validation/retained_evidence.json` | PASS | Positive diagonal objective and constraint rescalings |
| Domain monotonicity, budget monotonicity and concavity | exact profile corpus; unit tests | PASS | Finite domains |
| Feasible-domain flatness | controlled exact cases and formal proof | PASS | Active multipliers only |
| Finite minimax stress dual | exact primal-dual reconstruction; certificate replay | PASS | Finite rational data in retained objects |
| Harmless/repairable/irreparable trichotomy | 84 balanced cases, 28 per class | PASS | Retained finite corpus |
| Exact minimum-budget formula | 84 minimum-budget certificates and KKT replay | PASS | Explicit retained objects |
| Rational piecewise-affine profile | exact profile vertices and breakpoint checks | PASS | Explicit rational finite data |
| Minimum-budget row generation | structured and explicit separators versus complete-domain baseline | PASS | No polynomial oracle-call bound |
| Fixed-budget profile row generation | 196 exact profile agreements | PASS | Retained budgets |
| Exact augmented-Chebyshev interval | finite-image checks with exact tie and failure above the threshold | PASS | Retained finite images |
| Conservatism of the former bound | constructive proof and retained ratio corpus | PASS | Empirical ratios are corpus-specific |
| Normalised perturbation radius | formal inequality and boundary-case tests | PASS | Feasibility and active set remain fixed |
| Row economy | retained challenger fractions and oracle-call records | PASS | Assignment and layered acyclic paths only |
| Runtime advantage | small and scaling timing records | CONDITIONAL | Not universal; scaling baseline is numerical |
| Cross-platform reproducibility | `.github/workflows/ci.yml` | OPEN | Hosted workflow not yet run publicly |
| Independent replication | external replication protocol | OPEN | Requires a second physical machine |
| Independent literature review | `docs/RELATED_WORK_AND_BENCHMARK_BOUNDARIES.md` | OPEN | Requires external subject-matter review |
