import json, sys
from pathlib import Path
from prc.presentation.infographic import infobrief, gate
R = Path('artifacts/output-v14')
for sid in sys.argv[1:]:
    m = json.loads((R/'prepared'/sid/'map.json').read_text()); b = json.loads((R/'boards'/sid/'board.json').read_text())
    d = gate(R/'infographics'/sid/'candidate-01.png', infobrief(m, m.get('brief'), b))
    print(sid, d.verdict, 'missing', [x[0] for x in d.missing], 'invented', [x[0] for x in d.invented][:12], flush=True)

