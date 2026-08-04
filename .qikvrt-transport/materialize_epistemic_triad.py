#!/usr/bin/env python3
"""Build the clean, atomic epistemic-triad successor from a transport carrier.

The transport branch is noncanonical.  This program searches its candidate Git
blobs for the two exact owner-supplied JPEG byte strings, copies the reviewed
textual source set into a detached current-main worktree, verifies every bound
identity, and writes a source receipt.  It never performs Zenodo, IETF, release,
deployment, PASS, FINAL_PASS or EFFECT_ACK_DONE effects.
"""
from __future__ import annotations

import argparse
import ast
import base64
import binascii
import hashlib
import json
import pathlib
import shutil
from collections import deque
from typing import Any, Iterable

PUBLICATION_ID = "qikvrt-pre-spacetime-ontology-20260804-v1"
BUNDLE_RELATIVE = pathlib.PurePosixPath(
    "docs/publications/2026-08-04-pre-spacetime-ontology"
)

EXPECTED_IMAGES: dict[str, dict[str, Any]] = {
    "FIGURE_PROFESSIONAL_POSTER.jpeg": {
        "bytes": 447418,
        "sha256": "fe5af321bdf8f8f75bef7367c4fe49afc5239922f9477bb67bbaa14b552747e1",
        "git_blob_sha1": "314d445c5d4cb1d94b84ba19282a338ea438eb32",
    },
    "FIGURE_ORIGINAL_SKETCH.jpeg": {
        "bytes": 560967,
        "sha256": "9e6a58dd9f803a0fbe5f97ba36472ffff336f3a92e3989c54c4a50f51cf1c143",
        "git_blob_sha1": "5f16362b7dafd04cd5acaa8d0b70d5a618e2e5a3",
    },
}

TEXT_SOURCE_IDENTITIES: dict[str, dict[str, Any]] = {
    "SOURCE_FIGURE_INDEX.json": {
        "bytes": 2018,
        "sha256": "3e6eafecc7275ff161d2b3a2d043061224a1140c02f3c2478519c21f3c826307",
        "git_blob_sha1": "cae21c3daa247a66f2038d464aba55d6514eff86",
    },
    "EPISTEMIC_TRIAD_DE.md": {
        "bytes": 5186,
        "sha256": "c881c3b0fc628ab80152c9a91644df3b24e4c50475afdf4228ab1552d2e4cf69",
        "git_blob_sha1": "c386a1496b569a87efc0abefd2eb0e757a818a98",
    },
    "CLAIM_MATRIX.json": {
        "bytes": 3981,
        "sha256": "b5136ba03543dcf1f5294e3f3535426a291a706f3389d862f77fd7e6d297c9c7",
        "git_blob_sha1": "266f3fa6d245d99ad48c2d1d88d11ef116c7e88e",
    },
    "EVIDENCE_BOUNDARY.md": {
        "bytes": 3883,
        "sha256": "d25cab1b0965e71f0af696e1ec2cfb019c9fcb11329e9da8bbb1983181fb8f56",
        "git_blob_sha1": "528da892bc8e4c747369594c50d9350e78778b31",
    },
    "NEGATIVE_AND_BOUNDARY_TESTS.json": {
        "bytes": 3252,
        "sha256": "81e8fa43bc404be39998e25edee8d1d1bd1ea6475d7b9fe6c3a3d731e9010494",
        "git_blob_sha1": "2dad7b0373ad86ea60eb312d3b9e43d7eed56562",
    },
    "README.md": {
        "bytes": 2737,
        "sha256": "9fa1d2d41135ad9b55b8e2567c8747b4fb34555aec4cf07f5a7ff93b8880a112",
        "git_blob_sha1": "dfd2ebd1fe72bad8258ef52fef8e6a1d7f1b15ea",
    },
    "PUBLICATION_ROUTING.json": {
        "bytes": 3101,
        "sha256": "8e12c9ef3c8188c798016fd2ccd662f7925cbb65a476363a06d09951a798c68a",
        "git_blob_sha1": "f604d66e4f2faabc3ad7be6bf3028f07d2883a34",
    },
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(  # noqa: S324 - canonical Git object identity
        f"blob {len(data)}\0".encode("ascii") + data
    ).hexdigest()


def identity(data: bytes) -> dict[str, Any]:
    return {
        "bytes": len(data),
        "sha256": sha256(data),
        "git_blob_sha1": git_blob_sha1(data),
    }


def require_identity(data: bytes, expected: dict[str, Any], where: str) -> None:
    observed = identity(data)
    if observed != expected:
        raise SystemExit(
            "BLOCK: exact identity mismatch for " + where + ": "
            + json.dumps({"expected": expected, "observed": observed}, sort_keys=True)
        )


def text_candidates(data: bytes) -> Iterable[tuple[bytes, str]]:
    """Yield safe textual normalizations that may expose an encoded payload."""
    decodings = ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be")
    for encoding in decodings:
        try:
            text = data.decode(encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
        stripped = text.strip()
        if not stripped:
            continue
        try:
            yield stripped.encode("ascii"), f"decode:{encoding}:ascii"
        except UnicodeEncodeError:
            pass
        if stripped.startswith("data:") and "," in stripped:
            _header, payload = stripped.split(",", 1)
            try:
                yield payload.strip().encode("ascii"), f"decode:{encoding}:data-url"
            except UnicodeEncodeError:
                pass
        try:
            literal = ast.literal_eval(stripped)
        except (ValueError, SyntaxError, MemoryError, RecursionError):
            literal = None
        if isinstance(literal, bytes):
            yield literal, f"decode:{encoding}:python-bytes-literal"
        elif isinstance(literal, str):
            try:
                yield literal.strip().encode("ascii"), f"decode:{encoding}:python-string-literal"
            except UnicodeEncodeError:
                pass
        try:
            parsed = json.loads(stripped)
        except (json.JSONDecodeError, MemoryError, RecursionError):
            parsed = None
        if isinstance(parsed, str):
            try:
                yield parsed.strip().encode("ascii"), f"decode:{encoding}:json-string"
            except UnicodeEncodeError:
                pass


def base64_candidates(data: bytes) -> Iterable[tuple[bytes, str]]:
    compact = b"".join(data.split())
    if not compact or len(compact) % 4:
        return
    if len(compact) > 16 * 1024 * 1024:
        return
    try:
        decoded = base64.b64decode(compact, validate=True)
    except (binascii.Error, ValueError):
        return
    if decoded:
        yield decoded, "base64"


def variants(seed: bytes, max_depth: int = 4) -> Iterable[tuple[bytes, tuple[str, ...]]]:
    queue: deque[tuple[bytes, tuple[str, ...], int]] = deque([(seed, ("raw",), 0)])
    seen: set[str] = set()
    while queue:
        data, chain, depth = queue.popleft()
        digest = sha256(data)
        if digest in seen:
            continue
        seen.add(digest)
        yield data, chain
        if depth >= max_depth:
            continue
        for derived, label in (*text_candidates(data), *base64_candidates(data)):
            queue.append((derived, chain + (label,), depth + 1))


def discover_images(blob_dir: pathlib.Path) -> tuple[dict[str, bytes], list[dict[str, Any]]]:
    found: dict[str, bytes] = {}
    evidence: list[dict[str, Any]] = []
    candidates = sorted(path for path in blob_dir.iterdir() if path.is_file())
    if not candidates:
        raise SystemExit("BLOCK: no candidate carrier blobs are present")
    for candidate in candidates:
        raw = candidate.read_bytes()
        for data, chain in variants(raw):
            observed = identity(data)
            for target_name, expected in EXPECTED_IMAGES.items():
                if observed != expected:
                    continue
                previous = found.get(target_name)
                if previous is not None and previous != data:
                    raise SystemExit("BLOCK: conflicting exact candidates for " + target_name)
                found[target_name] = data
                evidence.append(
                    {
                        "target": target_name,
                        "carrier_path": candidate.as_posix(),
                        "transform_chain": list(chain),
                        **observed,
                    }
                )
    missing = sorted(set(EXPECTED_IMAGES) - set(found))
    if missing:
        inventory = [
            {"path": path.name, **identity(path.read_bytes())}
            for path in candidates
        ]
        raise SystemExit(
            "BLOCK: exact source images not reconstructed; missing="
            + ",".join(missing)
            + "; carrier_inventory="
            + json.dumps(inventory, sort_keys=True)
        )
    return found, evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--carrier-root", type=pathlib.Path, required=True)
    parser.add_argument("--worktree", type=pathlib.Path, required=True)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    args = parser.parse_args()

    carrier_root = args.carrier_root.resolve()
    worktree = args.worktree.resolve()
    source_dir = carrier_root / ".qikvrt-transport/source"
    blob_dir = carrier_root / ".qikvrt-transport/candidate-blobs"
    target_dir = worktree.joinpath(*BUNDLE_RELATIVE.parts)
    if not target_dir.is_dir():
        raise SystemExit("BLOCK: promoted publication directory is absent from current main")

    images, image_evidence = discover_images(blob_dir)

    copied_text: list[dict[str, Any]] = []
    for name, expected in TEXT_SOURCE_IDENTITIES.items():
        source = source_dir / name
        if not source.is_file():
            raise SystemExit("BLOCK: missing carrier source " + name)
        data = source.read_bytes()
        require_identity(data, expected, "carrier source " + name)
        destination = target_dir / name
        destination.write_bytes(data)
        require_identity(destination.read_bytes(), expected, "target source " + name)
        copied_text.append({"path": destination.relative_to(worktree).as_posix(), **expected})

    copied_images: list[dict[str, Any]] = []
    for name, expected in EXPECTED_IMAGES.items():
        data = images[name]
        require_identity(data, expected, "reconstructed image " + name)
        destination = target_dir / name
        destination.write_bytes(data)
        require_identity(destination.read_bytes(), expected, "target image " + name)
        copied_images.append({"path": destination.relative_to(worktree).as_posix(), **expected})

    source_index = json.loads((target_dir / "SOURCE_FIGURE_INDEX.json").read_text(encoding="utf-8"))
    if source_index.get("publication_id") != PUBLICATION_ID:
        raise SystemExit("BLOCK: source figure index publication_id mismatch")
    indexed = {
        item.get("path"): {
            "bytes": item.get("bytes"),
            "sha256": item.get("sha256"),
            "git_blob_sha1": item.get("git_blob_sha1"),
        }
        for item in source_index.get("figures", [])
        if isinstance(item, dict)
    }
    if indexed != EXPECTED_IMAGES:
        raise SystemExit("BLOCK: source figure index does not bind the exact images")

    receipt = {
        "schema": "qikvrt_epistemic_triad_source_materialization_receipt_v1",
        "publication_id": PUBLICATION_ID,
        "carrier_commit": None,
        "target_base": None,
        "image_discovery": image_evidence,
        "copied_images": copied_images,
        "copied_text_sources": copied_text,
        "external_effects": {
            "zenodo": False,
            "ietf": False,
            "release": False,
            "deployment": False,
        },
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
        },
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
