from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path

root, proof = (Path(value).resolve() for value in sys.argv[1:3])
revision = sys.argv[3]
checkout = Path((proof / "checkout.txt").read_text().strip())
archive = next((proof / "dist").glob("*.tar.gz"))
listed = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"]).decode().split("\0")
paths = [
    path
    for path in listed
    if path.startswith(("src/", "tests/", "scripts/")) or path in ("pyproject.toml", "uv.lock")
]
mismatches = []
archive_paths = []
for path in paths:
    expected = subprocess.check_output(["git", "-C", str(root), "show", f"{revision}:{path}"])
    if (checkout / path).read_bytes() != expected:
        mismatches.append({"path": path, "source": "verified checkout"})
with tarfile.open(archive) as source:
    members = {
        item.name.split("/", 1)[1]: item
        for item in source.getmembers()
        if "/" in item.name and item.isfile()
    }
    for path in paths:
        if path.startswith("src/") and path not in members:
            mismatches.append({"path": path, "source": "missing packaged source"})
    for path, member in members.items():
        if path == "PKG-INFO":
            continue
        assert path in listed, ("unexpected archive input", path)
        expected = subprocess.check_output(["git", "-C", str(root), "show", f"{revision}:{path}"])
        handle = source.extractfile(member)
        assert handle is not None
        if handle.read() != expected:
            mismatches.append({"path": path, "source": "archive"})
        archive_paths.append(path)
cases = ET.parse(proof / "tests.xml").findall(".//testcase")
assert cases and not mismatches, mismatches
assert all(case.find(name) is None for case in cases for name in ("failure", "error", "skipped"))
report = {
    "prc_commit": revision,
    "checkout": str(checkout),
    "archive": str(archive),
    "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    "verified_paths": len(paths),
    "verified_archive_paths": len(archive_paths),
    "archive_paths": sorted(archive_paths),
    "archive_excludes": "Tests and maintainer scripts are intentionally excluded by the sdist only-include configuration.",
    "mismatches": mismatches,
    "tests": len(cases),
    "skipped": 0,
    "scope": ["src/", "tests/", "scripts/", "pyproject.toml", "uv.lock"],
    "excludes": "Working audit, plan and documentation files are not code-byte evidence.",
    "cache": json.loads((proof / "cache-start.json").read_text()),
    "reused_assets": ["Chromium installation", "Kokoro weights"],
}
(proof / "source-archive-compare.json").write_text(json.dumps(report, indent=2) + "\n")
print(
    json.dumps(
        {
            key: report[key]
            for key in ("prc_commit", "verified_paths", "tests", "skipped", "mismatches")
        }
    )
)
