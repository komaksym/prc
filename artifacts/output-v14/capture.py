import importlib.util, json, subprocess
from pathlib import Path

WORK = Path('/Users/koval/dev/prc/.claude/worktrees/v3-study')
ROOT = WORK / 'artifacts/output-v14'
V4 = WORK / 'artifacts/output-v4'
spec = importlib.util.spec_from_file_location('materials', WORK / 'scripts/prepare_paired_materials.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
sel = [
    ('v14-ui', 'zauberzeug', 'nicegui', 6380, 'front-end: web UI framework, 3D scene element'),
    ('v14-game', 'pythonarcade', 'arcade', 2977, 'gaming: game engine sprite collision, performance'),
    ('v14-ml', 'scikit-learn', 'scikit-learn', 34386, 'ML: preprocessing encoders, performance'),
]
rows = []
for sid, o, n, num, kind in sel:
    pr = json.loads(subprocess.run(['gh', 'api', f'repos/{o}/{n}/pulls/{num}'], capture_output=True, check=True).stdout)
    out = ROOT / 'prepared' / sid
    (ROOT / 'source' / sid).mkdir(parents=True, exist_ok=True)
    (ROOT / 'source' / sid / 'pr.json').write_text(json.dumps(pr, indent=2) + '\n')
    if not out.exists():
        m.capture(m.GitHubSource(V4 / 'git-cache', transport=m.gh_transport), m.PrRef(o, n, num), pr['head']['sha'], out)
    mp = json.loads((out / 'map.json').read_text())
    assert mp['head_sha'] == pr['head']['sha']
    rows.append({'id': sid, 'kind': kind, 'pr_identity': f'{o}/{n}#{num}', 'url': pr['html_url'], 'title': pr['title'],
                 'head_sha': pr['head']['sha'], 'base_sha': pr['base']['sha'], 'merged_at': pr['merged_at'],
                 'files': [f['path'] for f in mp['files']]})
    print(sid, pr['html_url'], len(mp['files']), 'files', flush=True)
rule = 'v14: three public Python PRs of different kinds (front-end, gaming, ML perf), light look only'
(ROOT / 'selection.json').write_text(json.dumps({'rule': rule, 'prs': rows}, indent=2) + '\n')
