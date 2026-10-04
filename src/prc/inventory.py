"""Change Surface Inventory: exhaustive mechanical delta of the immutable Git trees."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from prc.gitutil import TreeChange, blob_size, read_blob, tree_delta, unified_diff
from prc.identity import InventoryId, content_id

MAX_INSPECTABLE_BYTES = 64 * 1024
ZERO_OID = "0" * 40
LFS_PREFIX = b"version https://git-lfs.github.com/spec/v1"

Surface = Literal["text", "binary", "lfs_pointer", "symlink", "submodule", "mode_only", "oversize"]
OPAQUE_SURFACES: frozenset[str] = frozenset({"binary", "lfs_pointer", "submodule", "oversize"})


@dataclass(frozen=True, slots=True)
class InventoryItem:
    item_id: str
    path: str
    status: str
    old_mode: str
    new_mode: str
    old_oid: str
    new_oid: str
    surface: Surface
    opaque: bool
    note: str
    added_lines: int
    removed_lines: int


@dataclass(frozen=True, slots=True)
class ChangeSurfaceInventory:
    inventory_id: InventoryId
    base_commit: str
    head_commit: str
    items: tuple[InventoryItem, ...]


def _classify(repo: Path, change: TreeChange) -> tuple[Surface, str]:
    if "160000" in (change.old_mode, change.new_mode):
        return "submodule", "submodule pointer; contents are not in this repository"

    if change.old_oid == change.new_oid:
        return "mode_only", f"mode {change.old_mode} -> {change.new_mode}"

    if "120000" in (change.old_mode, change.new_mode):
        return "symlink", "symlink target changed"

    new_blob = b"" if change.new_oid == ZERO_OID else read_blob(repo, change.new_oid)
    old_blob = b"" if change.old_oid == ZERO_OID else read_blob(repo, change.old_oid)

    if new_blob.startswith(LFS_PREFIX) or old_blob.startswith(LFS_PREFIX):
        return "lfs_pointer", "Git LFS pointer; object content is not in this repository"

    if b"\x00" in new_blob[:8192] or b"\x00" in old_blob[:8192]:
        return "binary", "binary content cannot be semantically inspected"

    largest = max(
        (blob_size(repo, oid) for oid in (change.old_oid, change.new_oid) if oid != ZERO_OID),
        default=0,
    )

    if largest > MAX_INSPECTABLE_BYTES:
        return (
            "oversize",
            f"{largest} bytes exceeds the {MAX_INSPECTABLE_BYTES} byte inspection limit",
        )

    return "text", ""


def _line_counts(repo: Path, change: TreeChange, surface: Surface) -> tuple[int, int]:
    if surface not in ("text", "symlink"):
        return 0, 0

    diff = unified_diff(repo, change.old_oid, change.new_oid)
    lines = diff.splitlines()
    added = sum(1 for line in lines if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in lines if line.startswith("-") and not line.startswith("---"))

    return added, removed


def build_inventory(repo: Path, base_commit: str, head_commit: str) -> ChangeSurfaceInventory:
    """Every changed tree entry becomes one item; uninspectable ones stay explicit."""

    items: list[InventoryItem] = []

    for change in sorted(tree_delta(repo, base_commit, head_commit), key=lambda entry: entry.path):
        surface, note = _classify(repo, change)
        added, removed = _line_counts(repo, change, surface)
        fields = (
            change.path,
            change.status,
            change.old_mode,
            change.new_mode,
            change.old_oid,
            change.new_oid,
        )
        items.append(
            InventoryItem(
                item_id=content_id("inv-item", fields),
                path=change.path,
                status=change.status,
                old_mode=change.old_mode,
                new_mode=change.new_mode,
                old_oid=change.old_oid,
                new_oid=change.new_oid,
                surface=surface,
                opaque=surface in OPAQUE_SURFACES,
                note=note,
                added_lines=added,
                removed_lines=removed,
            )
        )

    inventory_id = InventoryId(content_id("inventory", [base_commit, head_commit, items]))

    return ChangeSurfaceInventory(inventory_id, base_commit, head_commit, tuple(items))
