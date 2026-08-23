#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Create a canonical content-addressed manifest for VM and OCI release assets."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--source-head", required=True)
    parser.add_argument("--source-tree", required=True)
    parser.add_argument("--container-reference", default="")
    parser.add_argument("--container-digest", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    for name, value in (("source head", args.source_head), ("source tree", args.source_tree)):
        if len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
            raise SystemExit(f"BLOCK invalid {name}")
    if args.container_digest and not (
        args.container_digest.startswith("sha256:")
        and len(args.container_digest) == 71
        and all(ch in "0123456789abcdef" for ch in args.container_digest[7:])
    ):
        raise SystemExit("BLOCK invalid OCI manifest digest")

    root = Path(args.assets)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    excluded = {output.resolve()}
    assets = []
    for path in sorted((item for item in root.rglob("*") if item.is_file()), key=lambda item: item.relative_to(root).as_posix()):
        if path.resolve() in excluded or path.name.endswith("SHA256SUMS.txt"):
            continue
        relative = path.relative_to(root).as_posix()
        assets.append({
            "path": relative,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "download_url": f"https://github.com/Goldkelch/qik-vrt/releases/download/{args.tag}/{Path(relative).name}",
        })
    if not assets:
        raise SystemExit("BLOCK release asset set is empty")

    document = {
        "schema": "qikvrt_mesh_appliance_release_manifest_v1",
        "version": args.version,
        "tag": args.tag,
        "source": {
            "repository": "Goldkelch/qik-vrt",
            "head": args.source_head,
            "tree": args.source_tree,
        },
        "assets": assets,
        "oci": {
            "reference": args.container_reference or None,
            "digest": args.container_digest or None,
            "immutable_reference": (
                f"{args.container_reference.split(':v', 1)[0]}@{args.container_digest}"
                if args.container_reference and args.container_digest else None
            ),
            "platforms": ["linux/amd64", "linux/arm64"],
        },
        "effect_ack": {
            "profile": "draft-lohmann-qikvrt-effect-ack-00",
            "standards_status": "experimental_individual_internet_draft_profile",
            "responsibility_protocol": "qikvrt_responsibility_protocol_v1",
            "bounded_protected_effect": "terminal_input",
            "external_effect": "NONE",
        },
        "claims": {
            "physical_megast_execution": False,
            "general_internet_reachability": False,
            "general_effect_ack_done": False,
            "pass": False,
            "final_pass": False,
        },
    }
    encoded = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    output.write_text(encoded, encoding="utf-8")
    output.with_suffix(output.suffix + ".sha256").write_text(
        f"{hashlib.sha256(encoded.encode()).hexdigest()}  {output.name}\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
