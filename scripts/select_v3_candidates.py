"""Select Study v3 candidate PRs (Phase B1)."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

# Lens CI markers, formerly shared with the retired paired-eval kit.
LENS_COMMENT_AUTHORS = ("coldtea-pr-lens[bot]", "github-actions[bot]")
LENS_STATE_MARKER_PREFIX = "<!-- pr-lens:state "
LENS_STICKY_MARKER = "<!-- pr-lens:sticky -->"

SINCE_DEFAULT = "2026-09-14"
MAX_CHANGED_LINES = 500
MAX_CHANGED_FILES = 10
SIZE_RATIO = 1.5
EXCLUDE_DIR_PREFIXES = (
    "reports/",
    "artifacts/",
    "infographic/",
    ".codex-",
    "docs/",
    "specs/",
    ".agents/",
    ".github/",
)
EXCLUDE_EXTENSIONS = (".md", ".png", ".jpg", ".jpeg", ".svg", ".json")
EXCLUDE_NAMES = (".gitignore", ".gitkeep")
WEB_EXTENSIONS = (".js", ".ts", ".tsx", ".jsx", ".html")
HEAD_SHA_RE = re.compile(r'"headSha":"([0-9a-f]{40})"')
PR_ID_RE = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+#[0-9]+")


def is_code_path(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    if name in EXCLUDE_NAMES:
        return False
    low = path.lower()
    if low.endswith(EXCLUDE_EXTENSIONS):
        return False
    if any(low.startswith(prefix) for prefix in EXCLUDE_DIR_PREFIXES):
        return False
    return not ("/reports/" in low or low.startswith("data/"))


def compute_stats(files: list) -> dict:
    code_lines = 0
    python_lines = 0
    web_lines = 0
    code_files = 0
    total_lines = 0
    for item in files:
        filename = str(item.get("filename", ""))
        changed = int(item.get("additions", 0)) + int(item.get("deletions", 0))
        total_lines += changed
        if not is_code_path(filename):
            continue
        code_lines += changed
        code_files += 1
        low = filename.lower()
        if low.endswith(".py"):
            python_lines += changed
        if low.endswith(WEB_EXTENSIONS):
            web_lines += changed
    return {
        "code_lines": code_lines,
        "python_lines": python_lines,
        "web_lines": web_lines,
        "code_files": code_files,
        "total_lines": total_lines,
        "total_files": len(files),
    }


def is_python_majority(stats: dict) -> bool:
    code = stats["code_lines"]
    py = stats["python_lines"]
    web = stats["web_lines"]
    if code <= 0 or py <= 0:
        return False
    if py <= code / 2:
        return False
    return py > web


def parse_lens_head(body: str) -> str | None:
    if LENS_STICKY_MARKER not in body:
        return None
    if LENS_STATE_MARKER_PREFIX not in body:
        return None
    match = HEAD_SHA_RE.search(body)
    return match.group(1) if match else None


def lens_matches_head(bodies: list, head: str) -> bool:
    return any(parse_lens_head(body) == head for body in bodies)


def can_pair(
    a_lines: int, b_lines: int, a_files: int, b_files: int, ratio: float = SIZE_RATIO
) -> bool:
    if a_lines <= 0 or b_lines <= 0:
        return False
    if max(a_lines, b_lines) / min(a_lines, b_lines) > ratio:
        return False
    return abs(a_files - b_files) <= 1


def run_cmd(argv: list) -> str:
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError("command failed: " + " ".join(argv) + chr(10) + proc.stderr[:2000])
    return proc.stdout


def gh_json(argv: list):
    return json.loads(run_cmd(argv))


def list_prs(repo: str):
    return gh_json(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            repo,
            "--state",
            "all",
            "--limit",
            "100",
            "--json",
            "number,title,createdAt,mergedAt,state,baseRefOid,headRefOid",
        ]
    )


def pr_files(repo: str, number: int):
    # gh pr view paginates internally, so one call lists every file.
    data = gh_json(["gh", "pr", "view", str(number), "--repo", repo, "--json", "files"])
    out: list = []
    for item in data.get("files", []):
        out.append(
            {
                "filename": str(item.get("path", "")),
                "additions": int(item.get("additions", 0)),
                "deletions": int(item.get("deletions", 0)),
            }
        )
    return out


def lens_bodies(repo: str, number: int) -> list:
    rows = gh_json(
        [
            "gh",
            "api",
            "repos/" + repo + "/issues/" + str(number) + "/comments",
        ]
    )
    return extract_lens_bodies(rows if isinstance(rows, list) else [])


def extract_lens_bodies(rows: list) -> list:
    bodies: list = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        login = (row.get("user") or {}).get("login")
        if login not in LENS_COMMENT_AUTHORS:
            continue
        body = row.get("body") or ""
        if body:
            bodies.append(body)
    return bodies


def lens_comment_meta(repo: str, number: int) -> dict:
    try:
        rows = gh_json(
            [
                "gh",
                "api",
                "repos/" + repo + "/issues/" + str(number) + "/comments",
                "-q",
                '[.[] | select(.user.login=="coldtea-pr-lens[bot]") | {id: .id, url: .html_url}]',
            ]
        )
    except RuntimeError:
        return {}
    items = rows if isinstance(rows, list) else [rows]
    return items[0] if items else {}


def collect_excluded(roots: list) -> set:
    # Prior-study roster only: pr_identity values, familiar_pr_ids entries,
    # kit-exposed ids, and owner/repo#N strings inside prior-study trees.
    # A bare repo-wide grep overcounts (version pins, prose), so generic
    # matches count only under known study/packet directory names.
    # The current study's own v3-candidates outputs list every scanned PR,
    # so reading them back would exclude the whole pool on a rerun. Skip
    # them: only earlier studies and acceptance packets count.
    current_outputs = ("v3-candidates",)
    # Ids exposed by earlier demo studies, formerly shared with the retired kit.
    exposed_pr_ids = frozenset(
        {"willtho89/librarySync#98", "cybersemics/em#5756", "swarm-deploy/swarm-deploy#116"}
    )

    found: set = set(exposed_pr_ids)
    id_re = re.compile(r'"pr_identity"\s*:\s*"([^"]+)"')
    fam_re = re.compile(r'"familiar_pr_ids"\s*:\s*\[(.*?)\]', re.DOTALL)
    study_dirs = (
        "paired-study",
        "human-comparison",
        "acceptance",
        "replacements",
        "source-candidates",
        "prepared",
    )
    for root in roots:
        for base in [root / "artifacts", root / ".claude" / "worktrees"]:
            if not base.exists():
                continue
            for path in base.rglob("*.json"):
                if any(name in path.parts for name in current_outputs):
                    continue
                try:
                    content = path.read_text()[:200000]
                except OSError:
                    continue
                for hit in id_re.findall(content):
                    found.add(hit)
                for block in fam_re.findall(content):
                    for hit in PR_ID_RE.findall(block):
                        found.add(hit)
                if any(name in str(path) for name in study_dirs):
                    for hit in PR_ID_RE.findall(content):
                        found.add(hit)
    return found


def build_pool(repos: list, since: str, exclude_roots: list) -> tuple:
    excluded = collect_excluded(exclude_roots)
    pool: list = []
    scanned = 0
    for repo in repos:
        try:
            prs = list_prs(repo)
        except RuntimeError as exc:
            print("WARN list failed for " + repo + ": " + str(exc)[:200])
            continue
        if not isinstance(prs, list):
            continue
        for pr in prs:
            created = str(pr.get("createdAt", ""))
            merged = str(pr.get("mergedAt", "") or "")
            if created < since and merged < since:
                continue
            scanned += 1
            number = int(pr["number"])
            identity = repo + "#" + str(number)
            head = str(pr.get("headRefOid", ""))
            base = str(pr.get("baseRefOid", ""))
            try:
                files = pr_files(repo, number)
            except RuntimeError as exc:
                print("WARN files failed for " + identity + ": " + str(exc)[:160])
                continue
            stats = compute_stats(files if isinstance(files, list) else [])
            try:
                bodies = lens_bodies(repo, number)
            except RuntimeError:
                bodies = []
            pinned = lens_matches_head(bodies, head) if head else False
            reasons: list = []
            if identity in excluded:
                reasons.append("used-before")
            if not is_python_majority(stats):
                reasons.append("not-python-majority")
            if not pinned:
                reasons.append("lens-not-pinned")
            if stats["code_lines"] > MAX_CHANGED_LINES or stats["code_files"] > MAX_CHANGED_FILES:
                reasons.append("over-kit-size-cap")
            meta = lens_comment_meta(repo, number) if pinned else {}
            pool.append(
                {
                    "pr_identity": identity,
                    "repo": repo,
                    "number": number,
                    "title": str(pr.get("title", "")),
                    "state": str(pr.get("state", "")),
                    "createdAt": created,
                    "mergedAt": merged,
                    "base_sha": base,
                    "head_sha": head,
                    "stats": stats,
                    "lens_pinned": pinned,
                    "lens_comment_id": meta.get("id"),
                    "lens_comment_url": meta.get("url"),
                    "excluded_reasons": reasons,
                    "eligible": not reasons,
                }
            )
    eligible = [p for p in pool if p["eligible"]]
    return pool, eligible, excluded, scanned


def greedy_pairs(eligible: list) -> tuple:
    by_repo: dict = {}
    for item in eligible:
        by_repo.setdefault(item["repo"], []).append(item)
    pairs: list = []
    leftovers: list = []
    pair_id = 1
    for repo in sorted(by_repo):
        items = sorted(by_repo[repo], key=lambda p: (p["stats"]["code_lines"], p["number"]))
        i = 0
        while i + 1 < len(items):
            a, b = items[i], items[i + 1]
            if can_pair(
                a["stats"]["code_lines"],
                b["stats"]["code_lines"],
                a["stats"]["code_files"],
                b["stats"]["code_files"],
            ):
                lo = min(a["stats"]["code_lines"], b["stats"]["code_lines"])
                hi = max(a["stats"]["code_lines"], b["stats"]["code_lines"])
                pairs.append(
                    {
                        "pair_id": pair_id,
                        "repo": repo,
                        "members": [a, b],
                        "ratio": round(hi / lo, 3),
                    }
                )
                pair_id += 1
                i += 2
            else:
                leftovers.append(
                    {
                        "repo": repo,
                        "a": a["pr_identity"],
                        "b": b["pr_identity"],
                        "ratio": round(
                            max(a["stats"]["code_lines"], b["stats"]["code_lines"])
                            / max(1, min(a["stats"]["code_lines"], b["stats"]["code_lines"])),
                            3,
                        ),
                    }
                )
                i += 1
        if i < len(items):
            leftovers.append({"repo": repo, "single": items[i]["pr_identity"]})
    return pairs, leftovers


def main() -> int:
    parser = argparse.ArgumentParser(description="Select Study v3 candidates (B1)")
    parser.add_argument("--repos", nargs="+", required=True)
    parser.add_argument("--since", default=SINCE_DEFAULT)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--exclude-roots", nargs="*", default=[])
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    exclude_roots = [Path(r) for r in args.exclude_roots] or [repo_root]
    try:
        import prc

        print("package: " + str(Path(prc.__file__).resolve()))
    except ImportError:
        print("package: import-failed")
    print("lens markers: " + LENS_STICKY_MARKER + " / " + LENS_STATE_MARKER_PREFIX)
    print("lens authors: " + ",".join(LENS_COMMENT_AUTHORS))
    print("repos: " + ",".join(args.repos) + " since: " + args.since)
    pool, eligible, excluded, scanned = build_pool(args.repos, args.since, exclude_roots)
    print("scanned prs since cutoff: " + str(scanned))
    print("pool rows: " + str(len(pool)) + " eligible: " + str(len(eligible)))
    print("excluded identities observed in artifacts: " + str(len(excluded)))
    print("exclude roots: " + ",".join(str(r) for r in exclude_roots))
    pairs, leftovers = greedy_pairs(eligible)
    print("strict pairs (ratio<=1.5, files within 1): " + str(len(pairs)))
    for pair in pairs:
        names = [
            m["pr_identity"]
            + "("
            + str(m["stats"]["code_lines"])
            + "/"
            + str(m["stats"]["code_files"])
            + ")"
            for m in pair["members"]
        ]
        print(
            "pair"
            + str(pair["pair_id"])
            + " "
            + pair["repo"]
            + " "
            + " + ".join(names)
            + " ratio="
            + str(pair["ratio"])
        )
    print("leftover notes: " + json.dumps(leftovers)[:2000])
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "pool.json").write_text(
        json.dumps(
            {"since": args.since, "repos": args.repos, "scanned": scanned, "rows": pool},
            indent=2,
            sort_keys=True,
        )
        + chr(10)
    )
    (out_dir / "strict_pairs.json").write_text(
        json.dumps({"pairs": pairs, "leftovers": leftovers}, indent=2, sort_keys=True) + chr(10)
    )
    print("wrote: " + str(out_dir / "pool.json"))
    print("wrote: " + str(out_dir / "strict_pairs.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
