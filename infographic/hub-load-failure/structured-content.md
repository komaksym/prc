# Hub load failure: diagnosis to enforcement

## Sections
1. SYMPTOM
   - Handed-off URL did not load.
   - Listener alive, no response.
2. ROOT CAUSE
   - Single handler thread.
   - One silent preconnect blocked every request.
   - Reproduced on a study copy.
3. FIX 5750d8d
   - Threading server.
   - 15 second connection timeout.
   - Request lock keeps state serial.
   - Regression test fails on the old server.
4. HANDOFF LEVER
   - One supervised detached server.
   - Exact URL loaded in Chromium.
   - Silent-connection check.
   - Handoff record and screenshot.
   - Guards fail without the recipe.
   - AGENTS rule row.
5. LIVE PROOF
   - Host request 200.
   - Browser loaded, zero page errors.
   - Study untouched, six readings pending.
