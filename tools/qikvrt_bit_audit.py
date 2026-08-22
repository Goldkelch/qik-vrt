#!/usr/bin/env python3
"""Bit-exact audit of the tracked Git tree at an exact commit.

Reads canonical blob bytes from the Git object database, never from prior receipts.
Produces a per-entry SHA-256 inventory and a length-prefixed canonical aggregate SHA-256.
"""
import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path


def git(*args: str, binary: bool = False):
    return subprocess.check_output(["git", *args], text=not binary)


def tree_entries(head: str):
    raw = git("ls-tree", "-rz", "--full-tree", head, binary=True)
    out = []
    for rec in raw.split(b"\0"):
        if not rec:
            continue
        meta, path = rec.split(b"\t", 1)
        mode, typ, oid = meta.split(b" ", 2)
        out.append((mode.decode("ascii"), typ.decode("ascii"), oid.decode("ascii"), path))
    return out


def audit(head: str):
    exact_head = git("rev-parse", "--verify", f"{head}^{{commit}}").strip()
    tree = git("rev-parse", "--verify", f"{exact_head}^{{tree}}").strip()
    entries = tree_entries(exact_head)
    aggregate = hashlib.sha256()
    inventory = []
    blob_count = 0
    byte_count = 0

    proc = subprocess.Popen(
        ["git", "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
    )
    assert proc.stdin is not None and proc.stdout is not None
    try:
        for mode, typ, oid, path_b in entries:
            content_digest = None
            size = 0
            object_type = typ
            if typ == "blob":
                proc.stdin.write((oid + "\n").encode("ascii"))
                proc.stdin.flush()
                header = proc.stdout.readline().rstrip(b"\n").split(b" ")
                if len(header) != 3:
                    raise RuntimeError(f"invalid cat-file header for {oid}: {header!r}")
                _, actual_type, size_b = header
                if actual_type != b"blob":
                    raise RuntimeError(f"expected blob {oid}, got {actual_type!r}")
                size = int(size_b)
                data = proc.stdout.read(size)
                trailer = proc.stdout.read(1)
                if len(data) != size or trailer != b"\n":
                    raise RuntimeError(f"short/corrupt cat-file stream for {oid}")
                content_digest = hashlib.sha256(data).hexdigest()
                blob_count += 1
                byte_count += size
            else:
                # Gitlinks/non-blob entries bind their exact object identity; their
                # external repository bytes are deliberately not claimed here.
                content_digest = hashlib.sha256(
                    ("git-object:" + typ + ":" + oid).encode("ascii")
                ).hexdigest()

            fields = [
                mode.encode("ascii"), typ.encode("ascii"), oid.encode("ascii"),
                path_b, str(size).encode("ascii"), bytes.fromhex(content_digest),
            ]
            for field in fields:
                aggregate.update(struct.pack(">Q", len(field)))
                aggregate.update(field)

            inventory.append({
                "mode": mode,
                "type": object_type,
                "oid": oid,
                "path": path_b.decode("utf-8", "surrogateescape"),
                "size": size,
                "sha256": content_digest,
            })
    finally:
        if proc.stdin:
            proc.stdin.close()
        proc.wait(timeout=30)
        if proc.returncode != 0:
            raise RuntimeError(f"git cat-file failed: {proc.returncode}")

    return {
        "schema": "qikvrt_full_tracked_tree_bit_audit_v1",
        "head_sha": exact_head,
        "tree_sha": tree,
        "entry_count": len(entries),
        "blob_count": blob_count,
        "tracked_blob_bytes": byte_count,
        "canonical_index_sha256": aggregate.hexdigest(),
        "hash_algorithm": "sha256",
        "source": "git_object_database",
        "external_gitlink_bytes_claimed": False,
    }, inventory


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--head", default="HEAD")
    p.add_argument("--receipt", default="/tmp/qikvrt-bit-audit.json")
    p.add_argument("--inventory", default="/tmp/qikvrt-bit-inventory.jsonl")
    args = p.parse_args()
    receipt, inventory = audit(args.head)
    Path(args.receipt).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with Path(args.inventory).open("w", encoding="utf-8") as f:
        for item in inventory:
            f.write(json.dumps(item, sort_keys=True, ensure_ascii=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
