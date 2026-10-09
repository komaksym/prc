# Final property-label review

Halley, gpt-6.1-sol at high, independently checked 1613a21..f4b2763.
It found no new regressions. Its 9,816 property identity probes and seven focused tests passed.
Its comment review found zero findings and no MUST KILL flags.
Evidence is regressions/final-label-review/probes.json and pytest.log.

It also reproduced a preexisting terminal-label limit. Cutting an escape entity can invalidate Mermaid syntax.
The parent accepted this issue within reliable rendering rather than leaving a known graph syntax failure.
Four new rendered-comment regressions failed first. Eighty label samples cover quote, hash and angle entities near the limit.
mermaid_label now retains complete entities and marks truncation with an ellipsis.
The focused suite passed sixteen checks after the correction.
Repeatable comment samples are in artifacts/e2e/long-mermaid-labels.
The corrected source needs its own fresh recheck and clean-cache proof.
