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
bash "$root/scripts/check-hygiene.sh"
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
# The listening E2E transcribes real speech. An offline check must run it; an online check
# names the gap instead of skipping, because this script fails on a skipped case.
if uv run $UV_OFFLINE python -c 'from prc.explainer.listen import find_engine; find_engine()' > "$proof/recognizer.log" 2>&1; then
  uv run $UV_OFFLINE pytest -q --junitxml="$proof/tests.xml" > "$proof/tests.log" 2>&1
elif [ -n "$UV_OFFLINE" ]; then
  echo "verify-release.sh --offline needs a speech recognizer to run the listening E2E: Muesli's muesli-cli or openai-whisper." >&2
  exit 2
else
  echo "verify-release.sh found no speech recognizer; deselecting the listening E2E rather than skipping it." >&2
  uv run $UV_OFFLINE pytest -q -m "not needs_recognizer" --junitxml="$proof/tests.xml" > "$proof/tests.log" 2>&1
fi
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
if [ -d "$hf_hub/models--hexgrad--Kokoro-82M" ]; then
  export HF_HUB_OFFLINE=1
elif [ -n "$UV_OFFLINE" ]; then
  echo "verify-release.sh --offline found no cached hexgrad/Kokoro-82M weights under $hf_hub; warm the cache once with network access instead of downloading during an offline check." >&2
  exit 2
fi
"$proof/wheel-env/bin/prc" doctor > "$proof/doctor.log"
python3 - "$checkout/tests/data/boards/shop.json" "$proof/board-code-names.json" <<'PY'
import json
import sys

board = json.load(open(sys.argv[1]))
board['scenes'][-1]['say'].append('Start review at `apply_discount` in cart.py, with the WELCOME10 code.')
json.dump(board, open(sys.argv[2], 'w'))
PY
"$proof/wheel-env/bin/prc" explain --source fixture:shop --board "$proof/board-code-names.json" --voice kokoro --infographic "$checkout/tests/data/infographic/shop-brief.png" --out "$proof/wheel-output" > "$proof/wheel-cli.json" 2> "$proof/wheel-cli.log"
if "$proof/wheel-env/bin/python" -c 'from prc.explainer.listen import find_engine; find_engine()' > "$proof/wheel-recognizer.log" 2>&1; then
  export PRC_RELEASE_LISTEN=1
elif [ -n "$UV_OFFLINE" ]; then
  echo "verify-release.sh --offline needs a speech recognizer to run the listening gate on the installed wheel." >&2
  exit 2
else
  echo "verify-release.sh found no speech recognizer; the listening gate on the installed wheel is not run here." >&2
fi
"$proof/wheel-env/bin/python" - "$proof" <<'PY'
import importlib.util
import json
import os
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
if os.environ.get('PRC_RELEASE_LISTEN') == '1':
    heard = subprocess.run(
        [str(proof / 'wheel-env' / 'bin' / 'prc'), 'listen', str(folder)],
        capture_output=True, text=True,
    )
    assert heard.returncode == 0, heard.stdout + heard.stderr
    listening = json.loads((folder / 'listening.json').read_text())
    assert listening['passed'] and listening['calibration']['passed'], listening['lost']
    assert {'apply_discount', 'cart.py', 'WELCOME10'} <= {t['token'] for t in listening['tokens']}
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
    page.wait_for_function("() => getComputedStyle(document.querySelector('#drawer')).transform === 'none'")
    page.screenshot(path=str(screenshots / 'map-drawer.png'))
    page.keyboard.press('Escape')
    assert page.locator('#drawer').get_attribute('aria-hidden') == 'true'
    page.wait_for_function("() => document.querySelector('#drawer').getBoundingClientRect().left >= innerWidth")
    page.screenshot(path=str(screenshots / 'map-closed.png'))
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
