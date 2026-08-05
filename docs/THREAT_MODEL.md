# Threat model

HAC treats the operating agent as potentially faulty, compromised, strategically evasive, or simply
confused. It also assumes requirements and authoring tools can be wrong.

## Protected goals

- keep actions within explicitly delegated identity, resource, and budget bounds;
- preserve inherited hard constraints across contract decomposition;
- detect modification or version confusion in activated contract graphs;
- stop known enforceable violations before mediated tool side effects;
- retain rule-level evidence for audit and higher-level assurance.

## In-scope failure modes

| Threat | Prototype control |
|---|---|
| subject adds its own authority | issuer/subject relationship plus attenuation checks |
| child drops a parent safety rule | effective policy always unions ancestor rules |
| child reuses a rule id with weaker content | `RULE_REWRITE` validation failure |
| parent contract changes beneath a child | exact parent digest pin |
| sibling delegations exceed parent budget | allocation conservation check |
| stolen/overbroad credential | action/resource/expiry/depth/version caveats |
| action violates history or deadline | preflight and finite-trace monitor |
| active content changes in memory | immutable values and firewall digest snapshot |
| approver equivocates about activation order | hash-linked activation receipts |

## Explicitly out of scope in 0.1

- an agent with direct access to a tool that bypasses the firewall;
- host, keyring, manager, Python runtime, or audit-store compromise;
- collusion between issuers, key holders, and operators;
- arbitrary natural-language semantic correctness;
- completeness, consistency, non-vacuity, or realizability of general requirements;
- unobservable actions, covert channels, prompt injection in upstream classifiers, or false telemetry;
- distributed replay protection, revocation, consensus, durable transparency logs, or non-repudiation;
- safety claims for stochastic models, continuous systems, or unbounded traces;
- preventing a legitimately authorized human from approving a harmful root contract.

## Deployment assumptions

A serious implementation must isolate the manager and firewall from operating agents; force all
side-effecting tools through authenticated mediation; source time and identity from trusted systems;
protect asymmetric keys in a KMS; support rapid revocation; and make audit logs append-only outside
the agent's write authority. Monitors must fail closed for safety-critical actions, with an explicit
human-controlled recovery path.

The strongest remaining risk is specification error. Independent review, adversarial requirement
testing, mutation tests, counterexample review, and operational feedback are part of the safety case,
not optional polish.

