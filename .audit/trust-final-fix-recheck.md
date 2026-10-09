# Final fix recheck at 1613a21

Mill, gpt-6.1-sol at max, independently reviewed 334e1f8..1613a21.
It reproduced one label-shortening regression. Other targeted checks passed, including 918 wrapping cases and three malformed-board CLI probes.

Keeping the full qualifier for a terminal bracket property made a long outer identifier fill the 60-character Mermaid label limit.
Truncation split an escape entity and made the emitted block fail its grammar gate.
The parent accepted the finding. Two new rendered-comment tests failed first, while four existing cases passed.
short_label now splits member boundaries outside quoted bracket segments.
Twelve focused Mermaid, bracket and hostile-input tests pass after the correction.

Evidence lives under artifacts/trustworthiness/2026-10-09/regressions/final-fix-recheck and long-bracket-label-{red,green}.log.
The earlier 1613a21 clean-cache run remains evidence for that checkpoint, not the final release proof.
A fresh bounded label recheck and clean-cache build will use the corrected commit.
