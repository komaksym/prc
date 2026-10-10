Test list. Every entry names the defect it catches.

## Part A: infographic step

1. test_infobrief_words_are_checked — brief lines derive only from
   card.headline / facts / look_first / risky / verdict / DISCLOSURE. Catches a
   brief that lets unchecked words enter the image vocabulary.
2. test_infobrief_deterministic — same map+board give byte-equal brief.json.
   Catches hidden clock or ordering in the brief.
3. test_gate_exact_match_passes — OCR text identical to the brief passes.
   Catches an over-strict gate that can never publish.
4. test_gate_missing_word_fails — image missing a headline word fails, and the
   word is named in the record. Catches publishing before reading.
5. test_gate_invented_word_fails — a gibberish token far from all allowed
   words fails. Catches invented model words reaching the PR comment.
6. test_gate_noise_tolerance — "checkouut" (one-glyph noise) passes;
   "check out" (split word) passes; "##" and short tokens are ignored; random
   5-letter garbage fails. Catches thresholds set too tight or too loose.
7. test_gate_unreadable_image — a blank image yields verdict unreadable, not a
   crash, and no publish. Catches a gate crashing on empty OCR output.
8. test_gate_without_tesseract — tesseract absent -> verdict tool, image not
   published, comment keeps the card. Catches dependence on an optional binary.
9. test_run_records_attempts — run.json lists each --infographic candidate
   with image sha256, prompt-file presence, and verdict; a failed candidate
   publishes nothing. Catches a pipeline that trusts the last candidate.
10. test_pass_embeds_after_gate_only — a passing candidate publishes
    infographic.png with identical bytes, and comment.md/doc.html embed it
    with the fixed disclosure alt; a failing one never embeds; the card
    fallback remains. Catches pre-gate embedding and post-gate repainting.
11. test_comment_doc_disclosure_present — the embed alt text and caption are
    the fixed DISCLOSURE sentence. Catches an unlabeled AI image.

## Part B: map rebuilt on PR Lens

12. test_bundle_matches_lock — committed prlens.bundle.js sha equals the lock
    entry; entry file and lock exist. Catches a stale or missing vendored
    bundle after a version bump.
13. test_graphdoc_ids_and_integrity (shop fixture) — every node id is
    s{i}/f{i}; every edge endpoint is a plotted node; every walkthrough focus
    id is a node; every node's lane exists. Catches referential breakage that
    would crash the page renderer.
14. test_graphdoc_limits — a synthetic 300-symbol/2000-edge map yields <=256
    nodes, <=512 edges, <=12 steps, labels within caps, and aggregate file
    nodes subtitle "N of M symbols shown". Catches silent contract overflow.
15. test_graphdoc_no_symbols_uses_file_nodes — a map with zero parsed symbols
    (the Go acceptance case) still emits one node per changed file and a
    >=2-step walkthrough. Catches the empty diagram.
16. test_graphdoc_deterministic — same ChangeMap, byte-equal doc; no
    generatedAt. Catches nondeterminism that would break hash identity.
17. test_graphdoc_delta_map — added/modified/deleted/context map to
    added/modified/removed/unchanged; exactly one hero edge (first tour edge).
    Catches status language drifting between prc and the renderer.
18. test_render_map_csp_and_data_block — CSP carries the two script hashes;
    the JSON block loads as an object; no symbol qualname appears outside the
    block. Catches CSP or injection regressions.
19. test_render_map_deterministic_bytes — two renders of one fixture are
    byte-identical, including the inlined bundle text. Catches page churn.
20. test_map_browser_hooks (playwright) — [data-node] click opens #drawer with
    apply_discount; Escape closes; #play/#zoom-in/#zoom-out/#zoom-fit;
    window.prcTour steps and seek(0); overlay boxes track the atlas; zero
    console errors. Catches player regressions on the real page, the only
    place the vendored browser-only bundle actually runs.
21. test_map_video_seeks_record (playwright, with board) — recording over
    prcTour.seek produces a video with distinct frames. Catches a broken
    camera path in the video pipeline.
22. test_map_cli_no_playwright_required — prc map renders without playwright
    installed. Catches an accidental playwright import in map-only paths.

Deletions and rewrites: test_map_layout.py and test_map_grouping.py are
deleted with the python layout; test_render_map.py, test_map_browser.py,
test_map_video.py and test_e2e_map.py are rewritten to the hook list above.
