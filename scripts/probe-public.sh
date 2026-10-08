#!/usr/bin/env bash
# Usage: scripts/probe-public.sh <proof-dir> [pull request URL ...]
# Clones the public repository into a temporary folder and installs it the
# way README.md says, with an empty uv cache. Then it runs prc doctor,
# renders the offline example, and runs a boardless explain on each pull
# request. Each step writes <step>.out and <step>.err in <proof-dir>.
# results.tsv has the exit code and seconds of each step. env.tsv records
# the commit, the token state, the uv cache and the browser cache.
# The script exits 1 when any step fails.
# PRC_REPO_URL and PRC_REF select another repository or branch.
set -uo pipefail

if [ "$#" -lt 1 ]; then
	printf 'usage: %s <proof-dir> [pull request URL ...]\n' "$0" >&2
	exit 1
fi

mkdir -p "$1"
proof=$(cd "$1" && pwd)
shift
repo_url=${PRC_REPO_URL:-https://github.com/komaksym/prc.git}
ref=${PRC_REF:-main}
work=$(mktemp -d "${TMPDIR:-/tmp}/prc-probe-XXXXXX")
export UV_CACHE_DIR="$work/uv-cache"
token=unset
if [ -n "${GITHUB_TOKEN:-}" ]; then
	token=set
fi
results="$proof/results.tsv"
failed=0
printf 'step\texit\tseconds\tsource\n' > "$results"
{
	printf 'started\t%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
	printf 'repo\t%s@%s\n' "$repo_url" "$ref"
	printf 'github_token\t%s\n' "$token"
	printf 'uv_cache\t%s, empty at start\n' "$UV_CACHE_DIR"
	printf 'browsers\t%s\n' "${PLAYWRIGHT_BROWSERS_PATH:-playwright default}"
	printf 'uv\t%s\n' "$(uv --version)"
	printf 'os\t%s\n' "$(uname -sr)"
} > "$proof/env.tsv"

step() {
	local name=$1 source=$2 start code
	shift 2
	start=$(date +%s)
	"$@" > "$proof/$name.out" 2> "$proof/$name.err"
	code=$?
	printf '%s\t%s\t%s\t%s\n' "$name" "$code" "$(($(date +%s) - start))" "$source" >> "$results"
	if [ "$code" -ne 0 ]; then
		failed=1
	fi
	return "$code"
}

step clone "$repo_url@$ref" git clone --quiet --branch "$ref" "$repo_url" "$work/prc" || exit 1
cd "$work/prc" || exit 1
printf 'head\t%s\n' "$(git rev-parse HEAD)" >> "$proof/env.tsv"
step sync uv.lock uv sync --extra video || exit 1
step doctor local uv run prc doctor
step example fixture:shop uv run prc explain --source fixture:shop --board tests/data/boards/shop.json --voice none --out "$proof/example"

n=0
for url in "$@"; do
	n=$((n + 1))
	step "pr$n" "$url" uv run prc explain --source "$url" --voice none --out "$proof/pr$n"
done

printf 'clone kept at %s\nuv cache at %s\nresults in %s\n' "$work/prc" "$UV_CACHE_DIR" "$results"
if [ "$token" = set ]; then
	printf 'GITHUB_TOKEN was set, so the pull request steps did not test the no-token path\n' >&2
fi
if [ "$failed" -ne 0 ]; then
	printf 'a step failed, see %s\n' "$results" >&2
	exit 1
fi
