# Test list: each names the defect it catches

## infographic

- spec_words_only_from_facts: catches prompt words the map cannot support (spec string absent from map/facts).
- prompt_file_written_before_generate: catches skill runs without a reproducibility record (no prompt file).
- gate_passes_exact_render: catches a gate that fails honest output (fixture png with all words must pass).
- gate_fails_invented_word: catches invented claims reaching outputs (one extra token forces fail).
- gate_fails_missing_number: catches dropped statistics (stat number absent forces fail).
- ocr_noise_tolerated: catches brittle matching (single-char/low-conf tokens never fail; edit-distance-1 on len>=5 passes).
- tesseract_absent_is_skipped: catches hard failure on machines without the binary (no tesseract -> skipped + card fallback).
- no_bitmap_repair: catches painted-over fixes (check record asserts regenerate path; overlay tools absent from module imports).
- comment_embeds_only_on_pass: catches AI-drawn image leaking past a failed gate (fail/skipped/absent renders card block).
- run_json_accumulates_attempts: catches overwritten history (two gates leave two attempt entries).

## lensdoc + player

- zero_symbol_map_has_file_nodes: catches the empty swarm-116 diagram (0 symbols still yields file nodes).
- node_cap_keeps_tour_first: catches tour focus dropped under overflow (300-symbol map keeps tour ids, drops context).
- name_edges_are_muted: catches lost name-only meaning (resolution=name always yields emphasis muted).
- invalid_doc_fails_in_python: catches browser-time blanks (15+ lanes / 257 nodes / bad ids fail validate_lens_doc).
- walkthrough_bounds: catches contract rejection (tour with 1 or 20 steps yields 2..12 steps).
- label_lengths_capped: catches renderer rejection (120+ char qualname truncated with word boundary).
- data_node_hook_stable: catches broken video/tests (every s{i} hit rect exists; seek(t) pauses and moves camera).
- drawer_escape_contract: catches broken hooks (click s{i} opens drawer with callee text; Escape closes with aria-hidden true).
- csp_single_inline_script: catches CSP violation (page has one inline script whose sha matches the meta tag).
- no_node_at_runtime: catches runtime Node import (bundle contains no require(node:) except the crypto stub).
