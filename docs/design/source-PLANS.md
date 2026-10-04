# Architecture checkpoint plan

Summary: product scope is accepted and the renewed [critical-only architecture closure](critical-only-loop.md) completed after one fix cycle. Three fresh reviewers returned zero criticals and a separate fresh verifier closed all six original mechanisms with zero verified criticals. The success stopping rule was met, so Cycles 2 and 3 were skipped. Implementation remains at the user's checkpoint.

## Milestones

1. Ground: complete — product boundary, primary user flow, invariants, and MVP constraints defined.
2. Sketch: complete — three independent architecture candidates produced and cross-judged.
3. Grill: complete — product, evidence, reviewer experience, evaluation, artifact, freshness, and trust decisions exhausted and confirmed with the user.
4. Agree: product decisions confirmed. The later reconciled contract corrections are now applied and independently closed by the renewed critical-only run.
5. Historical interrogation: the previous three-cycle run stopped at its cap with six unresolved mechanisms. Its history remains in `decisions.tsv` and `final-verifier.md`. The separately authorized renewed run closed them in milestone 7; the old capped run was not retroactively changed into a success.
6. Reconcile: complete. The six historical findings were mapped to four architecture corrections and one evaluation gate.
7. Critical-only closure: complete after one fix cycle. Three fresh reviewers found zero criticals; a different fresh verifier closed all six original mechanisms and found zero additional criticals. All role handles are closed. Frozen sources, hashes, observed commands, and verdicts are preserved in `critical-only/cycle-1/`.
8. Implement: intentionally not started. Retain the user's checkpoint before implementation and freeze treatment identities before scored trials.
9. Scrap: if later implementation exposes repeated structural friction, re-ground and redesign.
