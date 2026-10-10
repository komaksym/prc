# Step 1 review triage

## Summary

The three completed model reviews found release-blocking correctness defects. Fix them before rebuilding acceptance artifacts. No human review has occurred.

## Act on

- Foreign short words and stopwords bypass the OCR allowlist. Muse, GLM and Sol reproduced this.
- Code tokens bypass exact matching through the l/i fold and split-token relief. Muse, GLM and Sol reproduced this.
- OCR tool failures drop readings silently. GLM and Sol reproduced a pass from one of four readings.
- The gate reads a mutable path after the pipeline hashes another byte snapshot. GLM and Sol identify two separate reads.
- Mandatory brief content can exceed MAX_WORDS. Muse and Sol provide valid over-budget inputs.
- Inline infographics overflow the walkthrough. GLM and Sol identify absent image sizing rules.
- Changed files without selected symbols disappear from navigation. Sol reproduces README.md and pyproject.toml loss.
- Node budgeting and omitted tour focus need regression tests. The 300-file hang claim did not reproduce because an existing guard handles the flood. Reduced-budget tests found negative-selection and priority defects. The replacement removes the repeated loop and keeps every selection bounded.
- Graph omissions and conversion failures are not disclosed. GLM and Sol identify unused drop counts and a false empty-state message.
- Re-vendoring overwrites a changed bundle pin; rendering does not verify it. Sol and Muse identify both gaps.
- Doctor reports failed tesseract probes as available. Sol reproduces the wrong diagnostic.
- Infographic comments omit the image upload instruction. All three identify the missing guidance.
- Report all missing lines even when the same image contains foreign words. GLM identifies incomplete redraw guidance.

## Limits and dismissed scope

- OCR cannot prove that a bitmap contains no extra words, symbols or misleading visual relationships. Correct the absolute promise and retain visual inspection. Small prose errors and text below the confidence floor remain known limits.
- QR-code scanning and hostile payload detection would expand this drawing workflow into an image-security product. Do not add them.
- Explain directory locking predates this delta and has finally cleanup. Recheck the stale-lock assertion before treating it as a new defect.
- Provenance URLs carry PR identity from the existing map. Do not widen URL policy without an observed unsafe consumer.
- Vendor manifest shims are acceptable only after inspecting the pinned upstream code and documenting the unused browser imports.

## Review status

Muse, GLM and gpt-6.1-sol completed. The inherited parent reviewer and comment agent failed with HTTP 429 and gave no verdict. Retry the comment pass on the final delta. Run an independent check after the fixes.
