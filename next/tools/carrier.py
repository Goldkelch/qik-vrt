#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Generated implementation: OpenAI Codex.
"""Import exact Git-bound components; restore them without the original checkout.

No branch guessing, remote fetch, source execution, overwrite, or history cleanup.
Objects are verified before publication and again during reconstruction.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

def call(binary, *args, data=None, binary_result=False):
    r = subprocess.run([str(binary), *map(str, args)], input=data, capture_output=True, timeout=30)
    if r.returncode:
        raise ValueError(r.stderr.decode(errors="replace"))
    return r.stdout if binary_result else json.loads(r.stdout)

def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], timeout=30)

def target_catalog(repo, ref, repository):
    head=git(repo,"rev-parse","--verify","--end-of-options",ref+"^{commit}").decode().strip()
    tree=git(repo,"rev-parse",head+"^{tree}").decode().strip()
    definitions=json.loads(git(repo,"show",head+":next/TARGET_ENTRYPOINTS.json"))
    files=[]
    for row in git(repo,"ls-tree","-rz",head,"next","src/effect_ack_core.c","include/qikvrt/effect_ack.h").split(b"\0"):
        if not row:continue
        metadata,path=row.split(b"\t",1);mode,kind,blob=metadata.decode().split()
        if kind!="blob" or mode not in ("100644","100755"):raise ValueError("REGULAR_TARGET_SOURCE_REQUIRED")
        data=git(repo,"cat-file","blob",blob)
        files.append({"path":path.decode(),"mode":mode,"git_blob":blob,"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()})
    available={f["path"] for f in files}
    if any(c["entrypoint"] not in available for c in definitions["components"]):raise ValueError("TARGET_ENTRYPOINT_MISSING")
    return {"schema":"qikvrt-component-catalog-v1","source":{"repository":repository,"head":head,"tree":tree},
        "components":definitions["components"],"files":files,
        "scope":"complete selected target source; external compilers and Cargo packages remain separately locked dependencies",
        "validation_transferred":False}

def put(binary, store, data):
    with tempfile.NamedTemporaryFile() as f:
        f.write(data); f.flush()
        value = call(binary, "put", store, f.name)
    if value["sha256"] != hashlib.sha256(data).hexdigest():
        raise ValueError("OBJECT_READBACK_MISMATCH")
    return value["sha256"]

def import_catalog(binary, store, repo, catalog):
    source = catalog["source"]
    for key in ("head", "tree"):
        if len(source[key]) != 40 or any(c not in "0123456789abcdef" for c in source[key]):
            raise ValueError("INVALID_EXACT_SOURCE")
    if git(repo, "rev-parse", source["head"] + "^{tree}").decode().strip() != source["tree"]:
        raise ValueError("SOURCE_TREE_MISMATCH")
    # Bind the selected paths to the tree, not merely to a caller's object list.
    actual = {}
    for row in git(repo, "ls-tree", "-rz", source["head"]).split(b"\0"):
        if not row: continue
        metadata, path = row.split(b"\t", 1)
        mode, kind, blob = metadata.decode().split()
        actual[path.decode()] = (mode, kind, blob)
    for entry in catalog["files"]:
        if actual.get(entry["path"]) != (entry["mode"], "blob", entry["git_blob"]):
            raise ValueError("PATH_BINDING_MISMATCH: " + entry["path"])
        data = git(repo, "cat-file", "blob", entry["git_blob"])
        if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError("SOURCE_BYTE_MISMATCH: " + entry["path"])
        if entry["mode"] not in ("100644", "100755"):
            raise ValueError("REGULAR_SOURCE_FILE_REQUIRED")
        put(binary, store, data)
    manifest_digest = put(binary, store, canonical(catalog))
    commands = []
    for component in catalog["components"]:
        name = component["id"]
        commands.append({"event_id": "import:" + manifest_digest[:32] + ":" + name,
            "node_id": name,
            "subject": {**source, "subject_id": name},
            "cause_event_ids": [],
            "operation": {"op": "register", "artifact": manifest_digest, "entrypoint": component["entrypoint"]}})
    raw = subprocess.run([str(binary), "run", str(store)], input=b"".join(canonical(c)+b"\n" for c in commands), capture_output=True, timeout=60)
    results = [json.loads(line) for line in raw.stdout.splitlines()]
    if raw.returncode or len(results) != len(commands) or any(r.get("state") != "PERSISTED" for r in results):
        raise ValueError("REGISTRATION_INCOMPLETE: " + raw.stdout.decode(errors="replace"))
    return {"state": "IMPORTED", "catalog_sha256": manifest_digest,
        "files": len(catalog["files"]), "components": len(commands), "source": source,
        "scope": "source_preservation_and_discovery", "working_hardware_claim": False}

def restore(binary, store, digest, destination):
    data = call(binary, "get", store, digest, binary_result=True)
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError("MANIFEST_DIGEST_MISMATCH")
    catalog = json.loads(data)
    if catalog["schema"] != "qikvrt-component-catalog-v1":
        raise ValueError("UNKNOWN_CATALOG")
    # Validate every destination before making the new reconstruction directory.
    seen = set()
    for entry in catalog["files"]:
        path = PurePosixPath(entry["path"])
        if path.is_absolute() or not path.parts or any(p in (".", "..") for p in path.parts) or str(path) != entry["path"] or str(path) in seen:
            raise ValueError("UNSAFE_OR_DUPLICATE_SOURCE_PATH")
        if entry["mode"] not in ("100644", "100755"):
            raise ValueError("REGULAR_SOURCE_FILE_REQUIRED")
        seen.add(str(path))
    destination.mkdir(mode=0o700, parents=False, exist_ok=False)
    for entry in catalog["files"]:
        data = call(binary, "get", store, entry["sha256"], binary_result=True)
        if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError("RESTORE_BYTE_MISMATCH")
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if blob != entry["git_blob"]:
            raise ValueError("RESTORE_GIT_BLOB_MISMATCH")
        path = destination / entry["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as f: f.write(data)
        path.chmod(0o755 if entry["mode"] == "100755" else 0o644)
    return {"state": "RESTORED", "files": len(catalog["files"]), "catalog_sha256": digest,
        "destination": str(destination), "scope": "exact_selected_source_bytes", "executed": False}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("operation", choices=["catalog", "import", "restore"])
    p.add_argument("--binary", type=Path, default=ROOT/"target/release/qikvrt-next")
    p.add_argument("--store", type=Path)
    p.add_argument("--head", default="HEAD")
    p.add_argument("--repository", default="Goldkelch/qik-vrt")
    p.add_argument("--repo", type=Path, default=ROOT.parent)
    p.add_argument("--catalog", type=Path, default=ROOT/"component-catalog.json")
    p.add_argument("--digest")
    p.add_argument("--destination", type=Path)
    args = p.parse_args()
    if args.operation == "catalog":
        result=target_catalog(args.repo,args.head,args.repository)
    elif not args.store:
        p.error("import and restore require --store")
    elif args.operation == "import":
        result = import_catalog(args.binary, args.store, args.repo, json.loads(args.catalog.read_text()))
    else:
        if not args.digest or not args.destination: p.error("restore requires --digest and --destination")
        result = restore(args.binary, args.store, args.digest, args.destination)
    print(json.dumps(result, sort_keys=True))

if __name__ == "__main__": main()
