# Mathematical contract

## Finite model

Let `K` be a finite catalogue, `K0` its feasible subset and `x0` a selected
feasible candidate. A verification domain is any finite set

```text
K0 subseteq V subseteq K.
```

Objective and active-constraint differences are divided by positive scales
which are declared before domains are compared and are not recomputed after
domain enlargement.

## Verification-domain profile

For budget `B >= 0`, the profile is

```text
Gamma_V(B) = max min_x [lambda^T d(x) + nu^T h(x)]
             s.t. lambda >= 0, 1^T lambda = 1,
                  nu >= 0, 1^T nu <= B.
```

A non-negative value is a positive scalarisation certificate over `V`. A
positive value is a strict margin.

## Normative results

For every non-singleton finite domain:

- the profile maximum is attained
- a non-negative profile value certifies weak Pareto optimality on `K0`
- strictly positive objective weights certify Pareto efficiency
- a positive margin certifies uniqueness for the attached scalarisation
- the profile is invariant under positive changes of objective and constraint units
- domain enlargement cannot increase the profile
- the profile is non-decreasing, concave and continuous in the multiplier budget
- the profile is flat on the feasible domain
- a finite minimax dual represents the profile by sparse stress distributions
- rational finite data give a rational piecewise-affine profile
- domains are classified as harmless, repairable or irreparable by the minimum successful budget
- the minimum budget equals the worst exact stress-to-violation ratio
- exact row generation terminates finitely and returns a globally valid result

## Chebyshev interval

For a finite image and fixed positive Chebyshev weights, each competitor
contributes one affine inequality in the augmentation parameter. Their
intersection is the exact admissible interval. The earlier gap-over-range
quantity is only a sufficient lower bound on the upper endpoint and may be
arbitrarily conservative.

## Exclusions

The contract does not claim a frontier-generation method, a polynomial
oracle-call bound, a universal speed advantage or a compact negative integral
certificate of weighted-sum unsupportedness.
