/* Sketch of the rewritten src/prc/presentation/map_assets/map.js (part B).
 * One player. The vendored bundle (prlens.bundle.js) runs first and defines
 * window.prcLens = { render }. PR data enters only through #map-data JSON.
 */
(() => {
  const data = JSON.parse(document.getElementById("map-data").textContent);
  const doc = Object.freeze(data.graph);   // fully inflated GraphDoc
  const map = Object.freeze(data.map);     // map.json content (drawer, facts)

  // --- render ---
  // TODO: try { const out = prcLens.render(doc, {lens: "architecture", theme: "dark"}); }
  //       catch (error) { showFallbackBox("The diagram could not be drawn"); }
  //       PrLensRenderError must never become an uncaught page error.
  // TODO: <img id="world-img"> with data:image/svg+xml;base64,<svg>;
  //       record viewBox {w: out.width, h: out.height} for camera math.

  // --- geometry ---
  // TODO: atlas = out.atlas (lanes, nodes, edges as {x, y, width, height});
  //       scale = imgScale(viewBox, world box); resize hook re-fits.
  // TODO: buildHitTargets(): for each atlas.nodes[id] place a transparent
  //       <button class="hit" data-node="s{i}"|data-node="f{i}"> over the box;
  //       buttons carry no text.

  // --- camera (same math as today: fitTo/flyTo/zoomAt/applyCamera) ---
  // TODO: fit(), zoomAt(factor, sx, sy), flyTo(box, margin), drag + wheel.

  // --- tour ---
  // TODO: timeline = doc.walkthrough.steps map with kinds from data.stepKinds.
  // TODO: via(step): first plotted edge whose to == focus node (derive, not store).
  // TODO: captions: kicker per kind, main = step.heading, sub = symbolFacts(node).
  // TODO: window.prcTour = Object.freeze({ duration, steps: [...], seek(t) });
  //       step = { kind, focus, via, start, duration, caption }.

  // --- drawer (hook surface unchanged) ---
  // TODO: select(node): #drawer opens; sections built with el() and
  //       textContent only: qualname, path, status chip, added/removed,
  //       call_sites, hunk diff view, callers/callees from map.symbols/edges.
  // TODO: Escape closes (drawer aria-hidden true, drawer left >= innerWidth).

  // --- chrome ---
  // TODO: header stats chips from data.map.summary, meta line, title.
  // TODO: #play / #zoom-in / #zoom-out / #zoom-fit / progress bar wiring.
  // TODO: empty map (no nodes): same "no change in a parsed file" card.
  // TODO: fallback box on PrLensRenderError; page keeps working.
})();
