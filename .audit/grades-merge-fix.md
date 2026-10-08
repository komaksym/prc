# Grades merge fix: PASS

Verdict: PASS. Final grading merge is unblocked. Merger ran clean and wrote final outputs.

## Coverage

deterministic.json holds 480 rows with 70 NEEDS_HUMAN (c1 9, c2 11, c3 21, c4 24, c5 5).
Free grades cover all 70 with exact key match and no unknown or duplicate keys.

Grade files and counts:

- grades/free-c1c2.json: 20 grades (c1 9, c2 11), has input_sha256.
- grades/free-c3.json: 21 grades, has input_sha256.
- grades/free-c4.json: 24 grades, has input_sha256.
- grades/free-c5.json: 5 grades, has input_sha256 and input_count.

Grader inputs present: c1-pending, c2-pending, c3-pending, c4-pending, c5-pending,
free-c1c2, free-c3, free-c4, free-c5. Per-file grade keys equal input item keys.
Stored input_sha256 values match recomputed file hashes for all four files.
Note: at first read three grade files lacked input_sha256. By rerun time they
carried correct hashes. I did not edit any grade file.

Free-grade verdicts by condition: c1 partial 9. c2 partial 11. c3 correct 5,
partial 15, wrong 1. c4 correct 7, partial 17. c5 partial 3, wrong 2.
No cannot_tell in free grades.

## Merger run

Command: python3 artifacts/release/merge-release-grades.py. Exit 0.
py_compile passes. Frozen deterministic rows verified unchanged (410 of 410).
final-grades.json holds 480 rows: 70 independent free text, 410 frozen
deterministic, 0 NEEDS_HUMAN left.

Final verdicts by condition (each n=96): c1 correct 34, partial 18,
cannot_tell 42, wrong 2. c2 correct 34, partial 23, cannot_tell 36, wrong 3.
c3 correct 37, partial 18, cannot_tell 22, wrong 19. c4 correct 45, partial 33,
cannot_tell 10, wrong 8. c5 correct 13, partial 15, cannot_tell 65, wrong 3.

## File SHAs (sha256)

- grades/free-c1c2.json 758961232ae826e4db8e1a62a4c2db7ff4998cf2d1e288c36c69448e8b6459d9
- grades/free-c3.json 4cbbec3fb60d1915870e84a627e94f64a8d859af370e88f9978d232b5010673d
- grades/free-c4.json f394cfb19bcb7026cc132e57c327a12dddbe88eed5769958f4099d6451921c05
- grades/free-c5.json d59966da4c4c00d13de188b877173fa513aafae155dac9b7e47e77f9813a71c2
- grader-inputs/free-c1c2.json 85ac95edfca5a61f593ce5ec834c06548814911c2e178ff28ee22c8870310745
- grader-inputs/free-c3.json 7eab5c7bc6de5fd02184ad36255a1c1022c333e301826209defbe37abd9d52e6
- grader-inputs/free-c4.json b4696bce92c3ee774dc0531811d12f9949c5f1df5a9b19e787de652324ffde4b
- grader-inputs/free-c5.json ee596c1c6986d79a551dc80be84101d185b6127d7daa7a6c3fb53fcb131e7518
- final-grades.json 84bc887ae3555a46135c0e2899fc6c0ef39f444b161449200d4e8b8480f4f772
- grades/reviewer-c1.json 2245ce1bd43a5c5ed5078e36bf54efae0a41eeb15e4de56b7ce8464a38741b89
- grades/reviewer-c2.json 1f3470ff5ec2d6f3bd8f6f5f27cc3751b9548e6ec57dc4439415b5e6b3a9265c
- grades/reviewer-c3.json 4c95a433bac6c38eaab90c266899cd3d9c5b0e2f397a59716d4c7dd0ac0d5105
- grades/reviewer-c4.json 27947cc1a446b17d1a9334e87a79c866c11faab82f349a2e5d876f4977c40bcc
- grades/reviewer-c5.json 8e4f2ed9431852509e58e7f2da84bf06eb897196f80d25b86d38f0e16584133a
- deterministic.json a5db3194a13ed8bf7160a7137c109954095db283cb5f8f0c4582abc1d61b5461

## Diff summary (only merger edited, no grade content touched)

File: artifacts/release/merge-release-grades.py (git-ignored path, no git diff).
Replaced one bare hash assert with six strict lines: grader-input existence,
missing-hash diagnostic, labeled hash equality, count check honoring
input_count, and per-file grade-key versus input-item equality. Global
unknown-or-duplicate rejection, verdict allowlist, and missing-grade assert
stay unchanged. Guarantees only gained strength.
