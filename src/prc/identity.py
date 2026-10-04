"""Content addressing: canonical JSON and typed sha256 identities."""

from __future__ import annotations

import dataclasses
import hashlib
import json
from typing import Any, NewType

CodeComparisonId = NewType("CodeComparisonId", str)
VerificationEvidenceId = NewType("VerificationEvidenceId", str)
SourceBasisId = NewType("SourceBasisId", str)
InventoryId = NewType("InventoryId", str)
ManifestId = NewType("ManifestId", str)
SnapshotId = NewType("SnapshotId", str)
SemanticArtifactId = NewType("SemanticArtifactId", str)
PublishedViewId = NewType("PublishedViewId", str)
PublicationKey = NewType("PublicationKey", str)


def to_jsonable(value: Any) -> Any:
    """Convert dataclasses, tuples and mappings into plain JSON values."""

    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: to_jsonable(getattr(value, field.name))
            for field in dataclasses.fields(value)
        }

    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]

    if isinstance(value, bytes):
        raise TypeError("bytes must be hashed or decoded before identity construction")

    return value


def canonical_json(value: Any) -> bytes:
    """Deterministic JSON: sorted keys, no whitespace, UTF-8, no NaN."""

    return json.dumps(
        to_jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_id(kind: str, value: Any) -> str:
    """Identity `<kind>:sha256:<hex>`; the kind is hashed in so kinds never collide."""

    digest = sha256_hex(kind.encode("utf-8") + b"\x00" + canonical_json(value))
    return f"{kind}:sha256:{digest}"
