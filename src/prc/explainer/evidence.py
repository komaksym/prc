"""Real UI evidence: PR body images plus one preview screenshot, never a fake screen.

PRC turns a pull request into a board, a narrated video, a clickable page and an
infographic. It reads only code, so a pull request that changes a screen shows
no real screen. This module collects real UI evidence without running the app:
images already in the pull request body, and one headless-Chrome screenshot of
a preview URL when the pull request names one. A board may show these images in
a ``screens`` scene; it must never draw a fake screen.
"""

from __future__ import annotations

import json
import re
import shutil
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

NOTICE = "This PR changes the UI. PRC did not run the app. See the PR on GitHub."

UI_EXTS = frozenset({".html", ".css", ".scss", ".sass", ".less", ".svelte", ".tsx", ".jsx", ".vue"})

# Folders that hold one screen each: web widgets, game states and scenes, desktop GUIs.
UI_DIRS = (
    "widgets/",
    "elements/",
    "templates/",
    "states/",
    "screens/",
    "scenes/",
    "menus/",
    "ui/",
    "gui/",
)

PREVIEW_HOSTS = ("hf.space", "vercel.app", "netlify.app", "readthedocs.build")

_MD_IMG = re.compile(r"!\[([^\]]*)\]\((https?://[^)\s]+)\)")
_IMG_SRC = re.compile(r"<img[^>]+src=[\"'](https?://[^\"']+)[\"']", re.IGNORECASE)
_USER_ATTACH = re.compile(r"https://github\.com/user-attachments/assets/[0-9a-fA-F\-\.]+")
_RAW_GH = re.compile(
    r"https://raw\.githubusercontent\.com/[^\s\)\"'<>]+?\.(?:png|jpg|jpeg|gif)(?:\?[^\s\)\"'<>]*)?",
    re.IGNORECASE,
)
_PREVIEW = re.compile(
    r"https?://[^\s\)\"'<>`]*?(?:hf\.space|vercel\.app|netlify\.app|readthedocs\.build)[^\s\)\"'<>`]*"
)
_ALT = re.compile(r"alt=[\"']([^\"']*)[\"']", re.IGNORECASE)
_TAG = re.compile(r"<[^>]+>")


def is_ui_path(path: str) -> bool:
    """A changed path that shows a screen: template, web or style file, snapshot image, widget, game state."""
    low = path.lower()
    if "template" in low:
        return True
    ext = "." + low.rsplit(".", 1)[1] if "." in low.rsplit("/", 1)[-1] else ""
    if ext in UI_EXTS:
        return True
    if ext in (".svg", ".png") and "snapshot" in low:
        return True
    return any(f"/{d}" in f"/{low}" for d in UI_DIRS)


def ui_reasons(files: list[dict[str, Any]]) -> list[str]:
    """Changed paths that make the pull request a UI change, in diff order."""
    out: list[str] = []
    for f in files:
        path = str(f.get("path", ""))
        if f.get("status") == "deleted":
            continue
        if is_ui_path(path):
            out.append(path)
    return out


def _clean_caption(text: str) -> str:
    text = _TAG.sub("", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip("-|*#> ")
    return text[:200]


def extract_media(body: str) -> list[dict[str, str]]:
    """Every image in the PR body, in order: markdown, img src, bare, raw."""
    found: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(url: str, alt: str | None) -> None:
        url = url.rstrip(".,;:")
        if url.endswith(")") and url.count("(") < url.count(")"):
            url = url.rstrip(")")
        if url in seen:
            return
        seen.add(url)
        found.append({"url": url, "alt": (alt or "").strip()})

    for m in _MD_IMG.finditer(body):
        add(m.group(2), m.group(1))
    for m in _IMG_SRC.finditer(body):
        tag = m.group(0)
        alt_m = _ALT.search(tag)
        add(m.group(1), alt_m.group(1) if alt_m else None)
    for m in _USER_ATTACH.finditer(body):
        add(m.group(0), None)
    for m in _RAW_GH.finditer(body):
        add(m.group(0), None)
    return found


def extract_preview_urls(text: str) -> list[str]:
    """Preview URLs in PR text: hf.space, vercel.app, netlify.app, readthedocs.build."""
    seen: set[str] = set()
    out: list[str] = []
    for m in _PREVIEW.finditer(text):
        url = m.group(0).rstrip(".,;:")
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def caption_for(url: str, alt: str | None, body: str) -> str:
    """Alt text or the nearest line of PR text, plain. GitHub's default alt "image" says nothing."""
    if alt and alt.strip() and alt.strip().lower() not in {"image", "screenshot", "img"}:
        return _clean_caption(alt)[:200] or "From the PR"
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if url in line or url.rstrip(")") in line:
            # The image line itself, then the closest text line above it.
            for near in [line, *reversed(lines[:i])]:
                cleaned = _clean_caption(near.replace(url, ""))
                if cleaned and cleaned.lower() not in {"image", "screenshot"}:
                    return cleaned[:200]
    return "From the PR"


def is_real_image(data: bytes) -> bool:
    """Magic bytes only: a link is not an image until the bytes say it is."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return True
    if data.startswith(b"\xff\xd8\xff"):
        return True
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return True
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
        return True
    head = data[:2048].lstrip()
    if head.startswith(b"<svg") or head.startswith(b"<?xml"):
        try:
            text = data[:8192].decode("utf-8", errors="ignore")
        except Exception:
            return False
        return "<svg" in text[:8192].lower()
    return False


def image_ext(data: bytes, url: str) -> str | None:
    """File extension for real image bytes, or None when the bytes are not an image."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return ".gif"
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
        return ".webp"
    head = data[:2048].lstrip()
    if head.startswith(b"<svg") or head.startswith(b"<?xml"):
        return ".svg"
    return None


def download(url: str, timeout: float = 20.0) -> bytes | None:
    """Download one URL with urllib; None when it is not reachable."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "prc-evidence/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return bytes(resp.read(8 * 1024 * 1024))
    except Exception:
        return None


def screenshot_preview(url: str, dest: Path, timeout_ms: int = 30000) -> bool:
    """One headless-Chrome screenshot of a preview URL; False when skipped."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return False
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 800})
                page.goto(url, wait_until="networkidle", timeout=timeout_ms)
                page.wait_for_timeout(1500)
                page.screenshot(path=str(dest))
            finally:
                browser.close()
        data = dest.read_bytes() if dest.exists() else b""
        return bool(data) and is_real_image(data)
    except Exception:
        try:
            if dest.exists():
                dest.unlink()
        except Exception:
            pass
        return False


def collect(
    pr_json: dict[str, Any], map_json: dict[str, Any], out_dir: str | Path
) -> dict[str, Any]:
    """Collect real UI evidence for one PR into out_dir/evidence.json.

    pr_json is the PR JSON with a ``body`` (full GitHub API JSON or pinned
    resources); map_json is the pinned map with ``files``. Images land in
    out_dir/evidence/; evidence.json lands in out_dir. At most four body images
    plus one preview screenshot. ``notice`` is set only when the PR changes the
    UI but carries no shot.
    """
    out = Path(out_dir)
    body = str(pr_json.get("body", "") or "")
    comments = pr_json.get("comments")
    extra_text = ""
    if isinstance(comments, list):
        parts: list[str] = []
        for c in comments:
            if isinstance(c, dict):
                parts.append(str(c.get("body", "") or ""))
            elif isinstance(c, str):
                parts.append(c)
        extra_text = "\n".join(parts)
    full_text = body + ("\n" + extra_text if extra_text else "")
    reasons = ui_reasons(list(map_json.get("files", [])))
    ui_change = bool(reasons)
    ev_dir = out / "evidence"
    ev_dir.mkdir(parents=True, exist_ok=True)
    # Drop stale shots so a rerun never mixes two PRs.
    for old in ev_dir.glob("shot-*"):
        old.unlink(missing_ok=True)
    shots: list[dict[str, str]] = []
    for item in extract_media(body)[:4]:
        data = download(item["url"])
        if not data or not is_real_image(data):
            continue
        ext = image_ext(data, item["url"]) or ".png"
        name = f"shot-{len(shots)}{ext}"
        (ev_dir / name).write_bytes(data)
        shots.append(
            {
                "path": name,
                "source": "pr-body",
                "source_url": item["url"],
                "caption": caption_for(item["url"], item.get("alt"), body),
            }
        )
    previews = extract_preview_urls(full_text)
    if previews:
        prev_name = f"shot-{len(shots)}.png"
        if screenshot_preview(previews[0], ev_dir / prev_name):
            shots.append(
                {
                    "path": prev_name,
                    "source": "preview",
                    "source_url": previews[0],
                    "caption": caption_for(previews[0], None, body),
                }
            )
    notice: str | None = None
    if ui_change and not shots:
        notice = NOTICE
    evidence: dict[str, Any] = {
        "ui_change": ui_change,
        "reasons": reasons,
        "shots": shots,
        "notice": notice,
    }
    (out / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return evidence


def load_beside(map_path: Path | None) -> dict[str, Any] | None:
    """The evidence.json that collect wrote beside a prepared map, or None."""
    if map_path is None:
        return None
    path = Path(map_path).parent / "evidence.json"
    if not path.is_file():
        return None
    data: dict[str, Any] = json.loads(path.read_text())
    return data


def copy_shots(board: dict[str, Any], src_root: Path, out: Path) -> None:
    """Copy every screens image beside the page and video, and point it at evidence/<file>.

    src_root is the prepared PR folder that holds evidence/ (or the evidence folder itself).
    A missing file is left unset so the render gate fails on the unloaded image.
    A shot that evidence.json marks as not from the PR body keeps its own source link,
    so the page never credits an archive copy to the PR description.
    """
    shots: dict[str, dict[str, Any]] = {}
    for ev_path in (src_root / "evidence.json", src_root.parent / "evidence.json"):
        if ev_path.is_file():
            shots = {
                str(sh.get("path")): sh
                for sh in json.loads(ev_path.read_text()).get("shots", [])
                if isinstance(sh, dict)
            }
            break
    for s in board.get("scenes", []):
        if s.get("type") != "screens":
            continue
        for img in s.get("images", []):
            if not isinstance(img, dict) or not isinstance(img.get("path"), str):
                continue
            name = Path(img["path"]).name
            found = next(
                (c for c in (src_root / "evidence" / name, src_root / name) if c.is_file()), None
            )
            if found is None:
                continue
            dest = out / "evidence" / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if found.resolve() != dest.resolve():
                shutil.copyfile(found, dest)
            img["src"] = f"evidence/{name}"
            label = source_label(shots.get(img["path"], {}))
            if label:
                img["source_label"] = label
                img["source_url"] = shots[img["path"]]["source_url"]


def source_label(shot: dict[str, Any]) -> str | None:
    """The link text for a shot that does not come from the PR description, else None."""
    url = str(shot.get("source_url", ""))
    if shot.get("source") == "archive":
        stamp = re.search(r"/web/(\d{8})", url)
        if stamp:
            day = datetime.strptime(stamp.group(1), "%Y%m%d")
            return f"Web archive copy, {day.day} {day:%b %Y}"
        return "Web archive copy"
    if shot.get("source") == "preview":
        return "Preview link"
    return None
