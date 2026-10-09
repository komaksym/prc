# Frozen delta review B

Reviewer. Russell, muse-spark-1.3-contributor at xhigh effort.
Scope. Immutable 6dbb336..334e1f8.
The parent stopped further investigation after the six-minute review window.
The reviewer returned findings already established and made no shared changes.

## Findings

1. High. Malformed Unicode escapes in quoted JavaScript keys crash parse_file.
   The generic regex fallback matches a lone backslash-u or backslash-x.
   unescape enters the Unicode branch and calls int with empty digits.
   Keys containing a malformed Unicode escape reproduced ValueError.
   index_tree does not catch that exception.

2. Medium. Mermaid labels split terminal bracket property names on their literal dot.
   short_label turns command["nested.run"] into run"].
   The emitted Mermaid text becomes run#quot;], which names no actual symbol.
   A bracket segment followed by .run still labels correctly.

## Parent judgment

Act on both findings. They have different roots from Lorentz's literal-backslash and wrapping findings.
Add failing parser and rendered-comment regressions before correcting the source.
The renderer, timing, board shape, facts and card fallback areas were read, with no further concrete findings.
This statement does not claim new verification runs for those areas.
