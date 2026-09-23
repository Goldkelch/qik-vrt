#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

REQUIRED_EQUAL_FIELDS = (
    "source_sha",
    "source_tree",
    "source_date_epoch",
    "contract_sha256",
    "snapshot",
    "toolchain",
)


def digest(path: pathlib.Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def load_receipt(path: pathlib.Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != "qikvrt.reference-linux-build-receipt.v1":
        raise ValueError(f"unsupported build receipt schema: {path}")
    return value


def verify(image_a: pathlib.Path, receipt_a_path: pathlib.Path,
           image_b: pathlib.Path, receipt_b_path: pathlib.Path) -> dict:
    receipt_a = load_receipt(receipt_a_path)
    receipt_b = load_receipt(receipt_b_path)
    for field in REQUIRED_EQUAL_FIELDS:
        if receipt_a.get(field) != receipt_b.get(field):
            raise ValueError(f"rebuild subject/toolchain drift: {field}")
    sha_a = digest(image_a)
    sha_b = digest(image_b)
    if receipt_a.get("sha256") != sha_a or receipt_b.get("sha256") != sha_b:
        raise ValueError("build receipt does not bind actual ISO bytes")
    if image_a.stat().st_size != receipt_a.get("bytes") or image_b.stat().st_size != receipt_b.get("bytes"):
        raise ValueError("build receipt byte count does not bind actual ISO bytes")
    if sha_a != sha_b or image_a.stat().st_size != image_b.stat().st_size:
        raise ValueError("REBUILD_SHA256_MATCH=false")
    return {
        "schema": "qikvrt.reference-linux-rebuild-receipt.v1",
        "source_sha": receipt_a["source_sha"],
        "source_tree": receipt_a["source_tree"],
        "source_date_epoch": receipt_a["source_date_epoch"],
        "contract_sha256": receipt_a["contract_sha256"],
        "snapshot": receipt_a["snapshot"],
        "toolchain": receipt_a["toolchain"],
        "artifact": "qikvrt-reference-linux-amd64.iso",
        "bytes": image_a.stat().st_size,
        "sha256_a": sha_a,
        "sha256_b": sha_b,
        "rebuild_sha256_match": True,
        "boot_witness_observed": False,
        "effect_ack_done": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image_a", type=pathlib.Path)
    parser.add_argument("receipt_a", type=pathlib.Path)
    parser.add_argument("image_b", type=pathlib.Path)
    parser.add_argument("receipt_b", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = verify(args.image_a, args.receipt_a, args.image_b, args.receipt_b)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"REBUILD_SHA256_MATCH sha256={result['sha256_a']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
