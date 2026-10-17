Source: PRC style arena round 7, candidate 3 handoff. Subject: pull request
https://github.com/komaksym/linkedin-mdp/pull/5 (merged, "Daily reconciliation
report in a Google Doc"), rendered as two page/video design directions.

Three moments on both pages: (1) The Google Doc report - left: this run,
status COMPLETE with six counts (Fetched rows 4, Matched rows 3, Unique
matched connections 2, Unmatched rows 1, Newly inserted events 1,
Already-present events 1); right: the Google Doc after the run (operator note
kept, [BEGIN AUTOMATED REPORT], "old" removed, new report written,
[END AUTOMATED REPORT], "Keep this note." kept). Links: e2e_doc_report.py:247
and :237. (2) Order of work in run() of scripts/report_connections_doc.py:
lines 36, 42, 43, 44, 50, 51, 66 with hidden folds 5/5/14; line 36 Google
checks run first; line 44 LinkedIn error gives BLOCKED; line 51 other errors
give FAILED, or BLOCKED if the LinkedIn client never started. (3) Summary:
"A daily workflow now writes reconciliation status into a private Google
Doc." Review tip: start at publish in google_doc_report.py:139; tests use
fake Google servers.

Direction 1 "Wondering" (wondering.app inspired): paper #FFFCF0, ink
#261312, Young Serif display + Public Sans body; meaning colours doc-blue
#7ACEFF, kept-green #5BBEA5, blocked-amber #E3B33C, failed-coral #FF7361;
keyword violet #6D4FC2, number orange #C46A16; Doc sheet is the hero object.

Direction 2 "Yours" - the review sheet (YC-product register): paper #FAFAF8,
ink #17181C, hairline #E7E7E3, Schibsted Grotesk + IBM Plex Mono; cobalt
#2E5CE6 marks the Doc-owned region; complete-green #146C43, blocked-amber
#8A5300, failed-red #B3261E; violet keywords #8250DF, orange numbers #953800;
three structurally different panels set on hairlines.

Shared: four test scenarios (complete, later_404, supabase_timeout, sharing)
switch moment 1; clip mode 1280x720, one moment at a time, one orchestrated
build-up per moment, window.__ready on fonts, window.__marks elapsed seconds
after each moment, window.__clipDone at end, about 13 s total; page view shows
the finished end state with no autoplay; keyboard focus and reduced motion
respected; responsive at 1440 and 800.

Verification: node --check passed on both script.js files; every file:line
reference is a clickable GitHub link; screenshots are the parent's pass
(sandbox cannot run Chromium; visual state unverified locally).
