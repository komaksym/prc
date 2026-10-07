#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
proof_root="$root/artifacts/release/verify"
mkdir -p "$proof_root"
proof=$(mktemp -d "$proof_root/run-XXXXXX")
checkout=$(mktemp -d "${TMPDIR:-/tmp}/prc-release-XXXXXX")
printf '%s\n' "$proof" > "$proof_root/latest-attempt.txt"
python3 - "$root" "$checkout" <<'PY'
import shutil
import subprocess
import sys
from pathlib import Path

root, checkout = map(Path, sys.argv[1:])
paths = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z']).decode().split('\0')
for pattern in ['tests/test_release*.py', 'tests/test_eval*.py', 'tests/test_explain_publication.py', 'scripts/verify-release.sh']:
    paths += [str(path.relative_to(root)) for path in root.glob(pattern)]
for name in paths:
    if name and (root / name).is_file():
        target = checkout / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / name, target)
for name in ['eval/runs/2026-10-06-full', 'docs/media']:
    shutil.copytree(root / name, checkout / name, dirs_exist_ok=True)
PY
printf '%s\n' "$checkout" > "$proof/checkout.txt"
cd "$checkout"
uv sync --frozen --offline > "$proof/sync.log" 2>&1
uv run --offline ruff check . > "$proof/lint.log" 2>&1
uv run --offline ruff format --check . > "$proof/format.log" 2>&1
uv run --offline mypy > "$proof/typecheck.log" 2>&1
uv run --offline pytest -q --junitxml="$proof/tests.xml" > "$proof/tests.log" 2>&1
python3 - "$proof/tests.xml" <<'PY'
import sys
import xml.etree.ElementTree as ET

cases = ET.parse(sys.argv[1]).findall('.//testcase')
assert cases, 'no tests collected'
skipped = [case.attrib for case in cases if case.find('skipped') is not None]
assert not skipped, f'release checks skipped: {skipped}'
PY
uv build --offline --out-dir "$proof/dist" > "$proof/build.log" 2>&1
cp -R artifacts/e2e "$proof/e2e"
printf 'Verified isolated release copy at %s\n' "$checkout"
uv venv --python "$checkout/.venv/bin/python" "$proof/wheel-env" > "$proof/wheel-env.log" 2>&1
uv pip install --offline --python "$proof/wheel-env/bin/python" "$proof/dist/prc-0.1.0-py3-none-any.whl[video]" > "$proof/wheel-install.log" 2>&1
mkdir -p "$proof/smoke"
cd "$proof/smoke"
"$proof/wheel-env/bin/prc" doctor > "$proof/doctor.log"
"$proof/wheel-env/bin/prc" explain --source fixture:shop --board "$checkout/tests/data/boards/shop.json" --voice none --out "$proof/wheel-output" > "$proof/wheel-cli.json" 2> "$proof/wheel-cli.log"
"$proof/wheel-env/bin/python" - "$proof" <<'PY'
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

proof = Path(sys.argv[1])
package = importlib.util.find_spec('prc')
assert package and package.origin and str(proof / 'wheel-env') in package.origin
result = json.loads((proof / 'wheel-cli.json').read_text())
folder = Path(result['out'])
assert result['check_passed'] is True
for name in ['map.html', 'video.mp4', 'doc.html', 'card.png', 'comment.md', 'run.json']:
    assert (folder / name).is_file(), name
probe = json.loads(subprocess.check_output([
    'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
    'stream=width,height,r_frame_rate:format=duration', '-of', 'json', str(folder / 'video.mp4')
]))
stream = probe['streams'][0]
assert (stream['width'], stream['height'], stream['r_frame_rate']) == (1920, 1080, '30/1')
screenshots = proof / 'screenshots'
screenshots.mkdir(exist_ok=True)
errors = []
with sync_playwright() as driver:
    browser = driver.chromium.launch()
    page = browser.new_page(viewport={'width': 1280, 'height': 800})
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto((folder / 'map.html').as_uri())
    page.wait_for_function('window.prcTour !== undefined')
    page.screenshot(path=str(screenshots / 'map.png'))
    nodes = page.locator('[data-node]')
    assert nodes.count() > 0, 'map has no symbols'
    change_map = json.loads((folder / 'map.json').read_text())
    checkout = next(i for i, symbol in enumerate(change_map['symbols']) if symbol['qualname'] == 'checkout')
    page.locator(f'[data-node="s{checkout}"]').click()
    assert page.locator('#drawer').get_attribute('aria-hidden') == 'false'
    assert 'apply_discount' in page.locator('#drawer').inner_text()
    page.screenshot(path=str(screenshots / 'map-drawer.png'))
    page.keyboard.press('Escape')
    assert page.locator('#drawer').get_attribute('aria-hidden') == 'true'
    page.set_viewport_size({'width': 800, 'height': 900})
    page.goto((folder / 'doc.html').as_uri())
    page.wait_for_function('window.docReady === true')
    assert page.locator('.shot').count() > 0, 'walkthrough has no scenes'
    page.screenshot(path=str(screenshots / 'doc.png'), full_page=True)
    assert not errors, errors
    browser.close()
board = json.loads((folder / 'board.json').read_text())
settled = next(scene['end'] - 0.5 for scene in board['scenes'] if scene['type'] == 'diff')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(settled), '-i', str(folder / 'video.mp4'),
                '-frames:v', '1', str(screenshots / 'video.png')], check=True)
(proof / 'wheel-check.json').write_text(json.dumps({'installed_package': package.origin, 'output': str(folder), 'probe': probe, 'screenshots': str(screenshots), 'browser_errors': errors}, indent=2))
print('Installed wheel produced all five outputs outside the source checkout.')
PY
printf '%s\n' "$proof" > "$proof_root/latest-success.txt"
