# Research lineage and design map

HAC is a synthesis prototype. It combines established contract-based design, temporal monitoring,
capability attenuation, and runtime enforcement with recent work on agent contracts. It does not
claim that these ideas originated here.

## Concept-to-implementation map

| HAC concept | Research basis | Prototype adaptation |
|---|---|---|
| hierarchical contract nets and assurance synthesis | Wang et al., *Hierarchical Contract-Based Synthesis for Assurance Cases* (NFM 2022) | objective/service/task graph and upward evidence model |
| assume/guarantee contracts, composition, refinement | Benveniste et al., *Contracts for System Design* (2018) | immutable `Contract`, inherited rules, structural `≼` checks |
| hierarchical decomposition | Filippidis & Murray, *Layering Assume-Guarantee Contracts for Hierarchical System Design* (2018) | root → service → task graph with parent digest pins |
| accessible requirement patterns over formal backends | Nuzzo et al., *CHASE* (DATE 2018) | fail-closed controlled-English compiler and reviewable rule IR |
| signal and metric temporal monitoring | Maler & Nickovic, *Monitoring Temporal Properties of Continuous Signals* (2004); Koymans, *Specifying Real-Time Properties with Metric Temporal Logic* (1990) | bounded response rules and finite timestamped traces |
| stochastic contracts | Nuzzo et al., *Stochastic Assume-Guarantee Contracts* (2019) | identified extension for probabilistic guarantees; not implemented |
| compositional assurance validation | Oh et al., *ARACHNE* (SAFECOMP 2022) | portfolio summaries and planned quantitative confidence aggregation |
| attenuating decentralized authorization | Birgisson et al., *Macaroons* (NDSS 2014) | action/resource/expiry/depth/version-bound capability chains |
| runtime suppression/intervention | Ligatti, Bauer & Walker, *Edit Automata* (2003) | independent pre-action `ALLOW/BLOCK` mediation |
| resource-bounded agent delegation | Ye & Tan, *Agent Contracts* (2026 preprint) | named allocations and sibling conservation law |
| temporal constraints for LLM tool use | Kamath et al., *Agent-C* (2025 preprint) | history-aware checks before tool release |

## Annotated references

1. **T. E. Wang, Z. Daw, P. Nuzzo, and A. Pinto (2022).**
   [*Hierarchical Contract-Based Synthesis for Assurance Cases*](https://doi.org/10.1007/978-3-031-06773-0_9).
   Introduces hierarchical contract nets and synthesis from libraries of refinement relations. This
   is the closest formal-methods antecedent to HAC's overall structure.

2. **A. Benveniste et al. (2018).** [*Contracts for System Design*](https://doi.org/10.1561/1000000053).
   A general contract meta-theory covering abstraction, composition, refinement, and methodological use.

3. **I. Filippidis and R. M. Murray (2018).**
   [*Layering Assume-Guarantee Contracts for Hierarchical System Design*](https://authors.library.caltech.edu/records/r6eba-5m902).
   Decomposes specifications while preserving realizability and hiding irrelevant variables.

4. **P. Nuzzo, M. Lora, Y. A. Feldman, and A. L. Sangiovanni-Vincentelli (2018).**
   [*CHASE: Contract-based requirement engineering for cyber-physical system design*](https://research.ibm.com/publications/chase-contract-based-requirement-engineering-for-cyber-physical-system-design).
   Connects a pattern-oriented requirements front end to rigorous contract analysis.

5. **O. Maler and D. Nickovic (2004).**
   [*Monitoring Temporal Properties of Continuous Signals*](https://doi.org/10.1007/978-3-540-30206-3_12).
   Introduces STL-style monitoring of bounded continuous-signal traces.

6. **R. Koymans (1990).**
   [*Specifying Real-Time Properties with Metric Temporal Logic*](https://doi.org/10.1007/BF01995674).
   Establishes an explicit metric treatment of time in temporal specifications.

7. **P. Nuzzo et al. (2019).**
   [*Stochastic Assume-Guarantee Contracts for Cyber-Physical System Design*](https://doi.org/10.1145/3243216).
   Uses stochastic STL contracts for probabilistic compatibility, consistency, refinement, and synthesis.

8. **C. Oh, N. Naik, Z. Daw, T. E. Wang, and P. Nuzzo (2022).**
   [*ARACHNE: Automated Validation of Assurance Cases with Stochastic Contract Networks*](https://doi.org/10.1007/978-3-031-14835-4_5).
   Models assurance cases as hierarchical stochastic contract networks and combines logical with
   Bayesian reasoning to assess soundness and confidence.

9. **A. Birgisson et al. (2014).**
   [*Macaroons: Cookies with Contextual Caveats for Decentralized Authorization in the Cloud*](https://research.google/pubs/macaroons-cookies-with-contextual-caveats-for-decentralized-authorization-in-the-cloud/).
   Demonstrates efficient delegated credentials whose caveats can only attenuate authority.

10. **J. Ligatti, L. Bauer, and D. Walker (2003).**
   [*Edit Automata: Enforcement Mechanisms for Run-time Security Policies*](https://cse.usf.edu/~ligatti/papers/TR-681-03.pdf).
   Formalizes runtime mechanisms that terminate, suppress, or insert actions to enforce policy.

11. **Q. Ye and J. Tan (2026).**
   [*Agent Contracts: A Formal Framework for Resource-Bounded Autonomous AI Systems*](https://arxiv.org/abs/2601.08815).
   Defines resource-bounded agent contracts, lifecycle semantics, and conservation across delegation.
   This is a recent preprint/accepted workshop contribution and should be treated accordingly.

12. **A. Kamath et al. (2025).**
    [*Enforcing Temporal Constraints for LLM Agents*](https://arxiv.org/abs/2512.23738).
    Compiles a temporal agent DSL to logic and intercepts non-conforming tool calls. This is a preprint.

## Where HAC is deliberately different

- The portfolio is about **behavioral and authority contracts**, not economic incentive contracts or
  blockchain smart contracts.
- It puts change control beside runtime enforcement: the subject may propose, but not mutate, an
  activated contract.
- It treats requirements translation as a separate trust boundary. LLM-generated formalizations
  are proposals that need review and independent checks.
- It connects technical rule evidence to organization-facing goals and metrics, while labeling that
  aggregation as an assurance argument—not an automatic proof of alignment.
