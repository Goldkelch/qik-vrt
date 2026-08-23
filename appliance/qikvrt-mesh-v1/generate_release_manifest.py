#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--source-head", required=True)
    parser.add_argument("--source-tree", required=True)
    parser.add_argument("--authority-base", required=True)
    parser.add_argument("--base-image", required=True)
    parser.add_argument("--container-reference", default="")
    parser.add_argument("--container-digest", default="")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = []
    for path in sorted(args.assets.iterdir(), key=lambda item: item.name):
        if (
            not path.is_file()
            or path == args.output
            or path.name.endswith("release.json.sha256")
        ):
            continue
        records.append(
            {
                "name": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "immutable_url": (
                    "https://github.com/Goldkelch/qik-vrt/releases/download/"
                    f"{args.tag}/{path.name}"
                ),
            }
        )
    value = {
        "schema": "qikvrt_mesh_appliance_release_v1",
        "version": args.version,
        "tag": args.tag,
        "source": {
            "repository": "Goldkelch/qik-vrt",
            "authority_base": args.authority_base,
            "head": args.source_head,
            "tree": args.source_tree,
        },
        "base_image": args.base_image,
        "container": {
            "reference": args.container_reference or None,
            "digest": args.container_digest or None,
            "immutable_reference": (
                args.container_reference + "@" + args.container_digest
                if args.container_reference and args.container_digest
                else None
            ),
        },
        "assets": records,
        "mutable_convenience_aliases_are_evidence": False,
        "firefox_distribution": "UPSTREAM_FIREFOX_ESR_PLUS_QIKVRT_ADAPTER",
        "effect_ack_profile": "draft-lohmann-qikvrt-effect-ack-01",
        "effect_scope": "BOUNDED_LOOPBACK_TERMINAL_INPUT_ONLY",
        "external_effect": "RELEASE_AND_GHCR_ONLY_WHEN_EXPLICITLY_PUBLISHED",
        "physical_megast_execution_claimed": False,
        "general_effect_ack_done_claimed": False,
        "pass_claimed": False,
        "final_pass_claimed": False,
    }
    args.output.write_text(
        json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    digest = sha256(args.output)
    args.output.with_suffix(args.output.suffix + ".sha256").write_text(
        f"{digest}  {args.output.name}\n", encoding="ascii"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
