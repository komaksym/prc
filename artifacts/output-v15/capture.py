import importlib.util, json, subprocess
from pathlib import Path

WORK = Path('/Users/koval/dev/prc/.claude/worktrees/v3-study')
ROOT = WORK / 'artifacts/output-v15'
V4 = WORK / 'artifacts/output-v4'
spec = importlib.util.spec_from_file_location('materials', WORK / 'scripts/prepare_paired_materials.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
sel = [
    ('v15-stepper', 'zauberzeug', 'nicegui', 6200, 'front-end: NiceGUI stepper done decoration'),
    ('v15-sparkline', 'Textualize', 'textual', 6171, 'front-end: Textual terminal UI sparkline height'),
    ('v15-oauth', 'gradio-app', 'gradio', 13767, 'front-end: Gradio workflow OAuth scope warning'),
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
rule = 'v15: three public front-end PRs that carry screenshots, to test real UI evidence'
(ROOT / 'selection.json').write_text(json.dumps({'rule': rule, 'prs': rows}, indent=2) + '\n')
