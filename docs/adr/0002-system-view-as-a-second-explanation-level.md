# System View as a second explanation level

The explainer gets a second level, the System View, next to the Code View. A System View board shows the System Parts that a pull request changes and the Behavioral Concepts that move between them. It shows no code lines on screen. Every box, arrow and caption still carries Evidence Links to the exact changed lines.

The System View reuses the Code View pipeline: the same map, board schema, board check, renderer, looks and page. It differs only in which scene kinds a board uses. A System View board has no `diff` scene. Coverage on the page therefore counts cited changed files, not changed lines on screen.

We chose this after a three-candidate arena on swarm-deploy/swarm-deploy#116. The candidates were a part map with a walk, a runtime sequence and an operator journey. The judge picked the part map with a walk. It kept one rule from the operator journey: draw no arrow whose wiring sits outside the diff, because the diff cannot support that arrow.

## Considered options

- A separate app or schema for system views. Rejected: it would split the board check, renderer and looks, and the flight test showed the existing scene kinds suffice.
- Code View with folded diffs. Rejected: the user asked for no code lines at all.

## Consequences

- Two levels now share one board check. The check still reports changed-line coverage, which reads as 0 for a System View. The page reports cited files instead.
- The infographic gate needs code relations. It returns "flat" for a System View and for languages without relation support, such as Go. A System View needs its own infographic brief before `prc explain` can publish one end to end.
- The renderer draws straight arrows and flat groups. System maps with nested packages or crossing paths need arrow routing and nested groups.
