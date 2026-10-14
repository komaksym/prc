#!/usr/bin/env bash
# Isolated release verification. Default mode is ONLINE: it bootstraps
# dependencies from uv.lock, so an empty uv cache works. Pass --offline for
# an explicit offline run, which requires a real warm uv cache and reuses
# the cached Chromium via PLAYWRIGHT_BROWSERS_PATH (never downloads).
set -euo pipefail

UV_OFFLINE=""
if [ "${1:-}" = "--offline" ]; then
  UV_OFFLINE="--offline"
  shift
fi
if [ "$#" -ne 0 ]; then
  echo "usage: scripts/verify-release.sh [--offline]" >&2
  exit 2
fi

if [ -n "$UV_OFFLINE" ]; then
  cache_dir="$(uv cache dir 2>/dev/null || true)"
  if [ -z "$cache_dir" ] || [ ! -d "$cache_dir" ] || [ -z "$(ls -A "$cache_dir" 2>/dev/null)" ]; then
    echo "verify-release.sh --offline needs a warm uv cache (empty or missing: ${cache_dir:-unknown}); run without --offline once to populate it from uv.lock." >&2
    exit 2
  fi
fi

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
sep = chr(0)
paths = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z']).decode().split(sep)
for name in paths:
    if name and (root / name).is_file():
        target = checkout / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / name, target)
for name in ['eval/runs/2026-10-06-full', 'docs/media']:
    src = root / name
    if src.exists():
        shutil.copytree(src, checkout / name, dirs_exist_ok=True)
PY
printf '%s\n' "$checkout" > "$proof/checkout.txt"
cd "$checkout"
uv sync --frozen --extra voice $UV_OFFLINE > "$proof/sync.log" 2>&1
uv run $UV_OFFLINE ruff check . > "$proof/lint.log" 2>&1
uv run $UV_OFFLINE ruff format --check . > "$proof/format.log" 2>&1
uv run $UV_OFFLINE mypy > "$proof/typecheck.log" 2>&1
uv run $UV_OFFLINE pytest -q --junitxml="$proof/tests.xml" > "$proof/tests.log" 2>&1
python3 - "$proof/tests.xml" <<'PY'
import sys
import xml.etree.ElementTree as ET

cases = ET.parse(sys.argv[1]).findall('.//testcase')
assert cases, 'no tests collected'
skipped = [case.attrib for case in cases if case.find('skipped') is not None]
assert not skipped, f'release checks skipped: {skipped}'
PY
uv build $UV_OFFLINE --out-dir "$proof/dist" > "$proof/build.log" 2>&1
if [ -z "${PLAYWRIGHT_BROWSERS_PATH:-}" ]; then
  echo "verify-release.sh needs PLAYWRIGHT_BROWSERS_PATH pointing at a cached Chromium; refusing to download browsers." >&2
  echo "Example: PLAYWRIGHT_BROWSERS_PATH=/path/to/browser-cache bash scripts/verify-release.sh" >&2
  exit 2
fi
if ! ls "$PLAYWRIGHT_BROWSERS_PATH"/chromium-* >/dev/null 2>&1; then
  echo "verify-release.sh found no chromium-* under PLAYWRIGHT_BROWSERS_PATH=$PLAYWRIGHT_BROWSERS_PATH; reuse the release browser cache instead of downloading." >&2
  exit 2
fi
export PLAYWRIGHT_BROWSERS_PATH

cp -R artifacts/e2e "$proof/e2e"
printf 'Verified isolated release copy at %s\n' "$checkout"
uv venv --python "$checkout/.venv/bin/python" "$proof/wheel-env" > "$proof/wheel-env.log" 2>&1
uv export --frozen --no-dev --extra video --extra voice --no-hashes --no-emit-project $UV_OFFLINE --output-file "$proof/dist/wheel-requirements.txt" > "$proof/wheel-export.log" 2>&1
uv pip install $UV_OFFLINE --python "$proof/wheel-env/bin/python" --requirement "$proof/dist/wheel-requirements.txt" "$proof/dist/prc-0.1.0-py3-none-any.whl[video,voice]" > "$proof/wheel-install.log" 2>&1
mkdir -p "$proof/smoke"
cd "$proof/smoke"
if [ -n "${HF_HUB_CACHE:-}" ]; then
  hf_hub="$HF_HUB_CACHE"
elif [ -n "${HF_HOME:-}" ]; then
  hf_hub="$HF_HOME/hub"
else
  hf_hub="$HOME/.cache/huggingface/hub"
fi
if [ ! -d "$hf_hub/models--hexgrad--Kokoro-82M" ]; then
  echo "verify-release.sh found no cached hexgrad/Kokoro-82M weights under $hf_hub; warm the cache once with network access instead of downloading during release verification." >&2
  exit 2
fi
export HF_HUB_OFFLINE=1
"$proof/wheel-env/bin/prc" doctor > "$proof/doctor.log"
python3 - "$checkout/tests/data/boards/shop.json" "$proof/board-code-names.json" <<'PY'
import json
import sys

board = json.load(open(sys.argv[1]))
board['scenes'][-1]['say'].append('Start review at `apply_discount` in cart.py, with the WELCOME10 code.')
json.dump(board, open(sys.argv[2], 'w'))
PY
"$proof/wheel-env/bin/prc" explain --source fixture:shop --board "$proof/board-code-names.json" --voice kokoro --out "$proof/wheel-output" --infographic "$checkout/artifacts/e2e/infographic/shop-diagram.png" > "$proof/wheel-cli.json" 2> "$proof/wheel-cli.log"
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
for name in ['video.mp4', 'page.html', 'infographic.png', 'comment.md', 'run.json']:
    assert (folder / name).is_file(), name
for name in ['map.html', 'doc.html', 'card.html', 'card.png']:
    assert not (folder / name).exists(), name
probe = json.loads(subprocess.check_output([
    'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
    'stream=width,height,r_frame_rate:format=duration', '-of', 'json', str(folder / 'video.mp4')
]))
stream = probe['streams'][0]
assert (stream['width'], stream['height'], stream['r_frame_rate']) == (1920, 1080, '30/1')
screenshots = proof / 'screenshots'
doctor = (proof / 'doctor.log').read_text()
assert 'kokoro ok' in doctor, doctor
run = json.loads((folder / 'run.json').read_text())
assert run['voice'] == 'kokoro', run['voice']
media = json.loads(subprocess.check_output([
    'ffprobe', '-v', 'error', '-show_entries',
    'stream=index,codec_type,duration:format=duration', '-of', 'json', str(folder / 'video.mp4')
]))
video_dur = float(media['format']['duration'])
audio = [s for s in media['streams'] if s.get('codec_type') == 'audio']
assert audio, 'video.mp4 has no audio stream'
assert audio[0].get('duration'), 'audio stream reports no duration'
assert abs(float(audio[0]['duration']) - video_dur) <= 0.5, (audio[0]['duration'], video_dur)
heard = subprocess.run(
    [str(proof / 'wheel-env' / 'bin' / 'prc'), 'listen', str(folder)], capture_output=True, text=True
)
assert heard.returncode == 0, heard.stdout + heard.stderr
listening = json.loads((folder / 'listening.json').read_text())
assert listening['passed'] and listening['calibration']['passed'], listening['lost']
assert {'apply_discount', 'cart.py', 'WELCOME10'} <= {t['token'] for t in listening['tokens']}
screenshots.mkdir(exist_ok=True)
errors = []
board = json.loads((folder / 'board.json').read_text())
diff = next(i for i, scene in enumerate(board['scenes']) if scene['type'] == 'diff')
with sync_playwright() as driver:
    browser = driver.chromium.launch()
    page = browser.new_page(viewport={'width': 1280, 'height': 800})
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto((folder / 'page.html').as_uri())
    page.wait_for_function('window.prcPage !== undefined')
    page.screenshot(path=str(screenshots / 'page.png'))
    page.click(f'#strip button:nth-child({diff + 1})')
    page.locator('#scale .pg-hit').first.click()
    page.wait_for_selector('#panel:not([hidden])')
    assert '/files#diff-' in (page.get_attribute('#panel-gh', 'href') or ''), 'hunk panel has no GitHub link'
    page.screenshot(path=str(screenshots / 'page-hunk.png'))
    page.click('#info-open')
    page.wait_for_function("document.querySelector('#info img').naturalWidth > 100")
    page.screenshot(path=str(screenshots / 'page-infographic.png'))
    assert not errors, errors
    browser.close()
settled = next(scene['end'] - 0.5 for scene in board['scenes'] if scene['type'] == 'diff')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(settled), '-i', str(folder / 'video.mp4'),
                '-frames:v', '1', str(screenshots / 'video.png')], check=True)
(proof / 'wheel-check.json').write_text(json.dumps({'installed_package': package.origin, 'output': str(folder), 'probe': probe, 'screenshots': str(screenshots), 'browser_errors': errors}, indent=2))
print('Installed wheel produced the video, page and infographic outside the source checkout.')
PY
printf '%s\n' "$proof" > "$proof_root/latest-success.txt"
