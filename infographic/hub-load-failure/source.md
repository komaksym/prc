# Source: hub load failure, diagnosis to enforcement (2026-10-13)

Operator report: the handed-off hub URL did not load.

Diagnosis: the server process stayed alive and held the listening socket, but it served
nothing. Root cause: the hub ran a single-threaded HTTPServer with no connection timeout.
One browser-style preconnect that sends no bytes blocks the only handler thread forever.
Every later request then times out. Reproduced in seconds on a study copy.

Fix, committed 5750d8d: ThreadingHTTPServer, a 15 second handler timeout, and one lock
that keeps request handling serialized. Regression test
test_silent_browser_connection_cannot_block_the_hub fails on the old server and passes on
the new one.

Handoff lever, built by the correct pass: scripts/handoff_study_hub.py starts or reuses one
detached hub, requires the exact URL to answer from the host, loads that URL in real
Chromium, drives Prepare next reading as a live check, holds a silent preconnect open and
requires the hub to keep answering, writes a handoff record with screenshot, and refuses to
print a URL when any check fails. Guards in tests/test_verify_paired_hub.py and
tests/test_dispatch_collection.py fail when the recipe or the rule row is missing. The rule
row lives in AGENTS.md.

Live proof: host request 200, Chromium load with zero page errors, silent connection did not
block the hub, sealed study untouched with six pending readings.
