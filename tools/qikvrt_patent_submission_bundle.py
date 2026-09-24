#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import pathlib
import zipfile

BASE = pathlib.Path("patent/meta-transistor/application-candidate-v1")
MANIFEST = BASE / "SUBMISSION_PACKAGE_MANIFEST.json"
CONTROL_FILES = [
    BASE / "SUBMISSION_FACTS.json",
    BASE / "SUBMISSION_PLAN.json",
    BASE / "UPLOAD_READINESS.json",
    BASE / "SUBMISSION_PACKAGE_MANIFEST.json",
    BASE / "FILING_READINESS.md",
]
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)

def load(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def git_blob_sha(data):
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()

def fail(msg):
    raise SystemExit(f"QIKVRT_SUBMISSION_BUNDLE_INVALID: {msg}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="meta-transistor-submission-staging.zip")
    parser.add_argument("--receipt", default="submission-staging-bundle-receipt.json")
    args = parser.parse_args()

    manifest = load(MANIFEST)
    if manifest.get("schema") != "qikvrt_submission_package_manifest_v1":
        fail("unexpected package manifest schema")

    source_paths = []
    source_receipts = []
    for entry in manifest.get("application_sources", []):
        raw_path = entry.get("path")
        declared = entry.get("blob_sha")
        if not raw_path or not declared:
            fail("source entry missing path or blob_sha")
        path = pathlib.Path(raw_path)
        if not path.is_file():
            fail(f"missing source file: {raw_path}")
        data = path.read_bytes()
        actual = git_blob_sha(data)
        if actual != declared:
            fail(f"source blob mismatch: {raw_path}: declared={declared} actual={actual}")
        source_paths.append(path)
        source_receipts.append({
            "path": raw_path,
            "git_blob_sha": actual,
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
        })

    bundle_paths = sorted(set(source_paths + CONTROL_FILES), key=lambda p: p.as_posix())
    for path in bundle_paths:
        if not path.is_file():
            fail(f"missing bundle control file: {path.as_posix()}")

    output = pathlib.Path(args.output)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as zf:
        for path in bundle_paths:
            data = path.read_bytes()
            info = zipfile.ZipInfo(path.as_posix(), FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            zf.writestr(info, data)

    bundle_bytes = output.read_bytes()
    receipt = {
        "schema": "qikvrt_submission_staging_bundle_receipt_v1",
        "subject": manifest.get("subject"),
        "execution_head": os.environ.get("GITHUB_SHA"),
        "role": "AUTOMATION_STAGING_BUNDLE_NOT_OFFICE_FILING_PAYLOAD",
        "office_filing_payload": False,
        "source_blob_bindings_verified": True,
        "bundle_path": output.as_posix(),
        "bundle_sha256": hashlib.sha256(bundle_bytes).hexdigest(),
        "bundle_size": len(bundle_bytes),
        "included_paths": [p.as_posix() for p in bundle_paths],
        "application_sources": source_receipts,
        "upload_ready": False,
        "filed": False,
        "filing_effect_ack_done": False,
    }
    pathlib.Path(args.receipt).write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))

if __name__ == "__main__":
    main()
