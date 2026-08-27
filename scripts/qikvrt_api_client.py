#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import stat
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

SAFE_REPOSITORY_COMPONENT = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9_.=-]{1,128}$")
SHA256_HEX = re.compile(r"^[0-9a-fA-F]{64}$")
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_GITHUB_DISPATCH_PAYLOAD_B64_CHARS = 48 * 1024


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Never forward a bearer credential through an HTTP redirect."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_regular_file(path: Path, *, max_bytes: int) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise OSError("path is not a regular file")
        if before.st_size > max_bytes:
            raise OSError(f"file exceeds {max_bytes} bytes")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise OSError(f"file exceeds {max_bytes} bytes")
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise OSError("file changed while being read")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def read_response(response) -> str:
    data = response.read(MAX_RESPONSE_BYTES + 1)
    if len(data) > MAX_RESPONSE_BYTES:
        raise ValueError("API response exceeds the 2 MiB client limit")
    return data.decode("utf-8")


def github_dispatch_transport_receipt(args: argparse.Namespace) -> dict[str, object]:
    """Describe GitHub's asynchronous 204 acceptance without promoting it.

    A successful workflow_dispatch request has no response body.  It proves
    only that GitHub accepted the transport request; execution and every
    downstream effect still require exact-run and artifact reobservation.
    """

    return {
        "schema": "qikvrt_github_dispatch_transport_ack_v1",
        "status": "TRANSPORT_ACCEPTED_ASYNC",
        "transport": f"github_{args.dispatch_kind}_dispatch",
        "repository": f"{args.owner}/{args.repo}",
        "workflow": "qikvrt_mesh_api.yml" if args.dispatch_kind == "workflow" else "default-branch repository_dispatch",
        "ref": args.ref,
        "request_id": args.request_id,
        "http_status": 204,
        "transport_ack": True,
        "effect_state": "EFFECT_ACK_CONTINUE",
        "ordinary_release": False,
        "next_observation": "bind the resulting workflow run and qikvrt-api-state artifact to the exact head",
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8766")
    ap.add_argument("--owner", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--ref", default="main")
    ap.add_argument(
        "--dispatch-kind",
        choices=["workflow", "repository"],
        default="workflow",
        help="GitHub-compatible transport; repository dispatch is default-branch bound.",
    )
    ap.add_argument("--operation", choices=["ingest", "verify", "stage", "release_status"], default="ingest")
    ap.add_argument("--artifact-id", default="qikvrt_artifact")
    ap.add_argument("--payload-file")
    ap.add_argument("--expected-sha256")
    ap.add_argument("--remote-evidence-file", help="Signed release-attestation JSON for release_status")
    ap.add_argument("--dry-run", default="true", choices=["true", "false"])
    ap.add_argument("--request-id", default="", help="Stable idempotency key; required for non-dry-run effects")
    ap.add_argument("--accept-effect", action="store_true", help="Explicitly accept the scoped non-dry-run effect")
    args = ap.parse_args()

    token = os.environ.get("QIKVRT_API_TOKEN", "")
    if not token:
        ap.error("QIKVRT_API_TOKEN must be supplied through the environment")
    if not SAFE_REPOSITORY_COMPONENT.fullmatch(args.owner):
        ap.error("--owner contains unsafe characters")
    if not SAFE_REPOSITORY_COMPONENT.fullmatch(args.repo):
        ap.error("--repo contains unsafe characters")
    if not SAFE_ID.fullmatch(args.artifact_id):
        ap.error("--artifact-id contains unsafe characters")
    if not SAFE_ID.fullmatch(args.request_id):
        ap.error("--request-id is required and must be a safe identifier")
    if not args.ref.strip() or len(args.ref) > 255:
        ap.error("--ref must contain 1 to 255 characters")
    if args.expected_sha256 and not SHA256_HEX.fullmatch(args.expected_sha256):
        ap.error("--expected-sha256 must be exactly 64 hexadecimal characters")
    parsed_base = urlparse(args.base_url)
    loopback_hosts = {"127.0.0.1", "localhost", "::1"}
    if parsed_base.scheme not in {"http", "https"} or not parsed_base.hostname:
        ap.error("--base-url must be an absolute HTTP(S) URL")
    if parsed_base.scheme != "https" and parsed_base.hostname not in loopback_hosts:
        ap.error("non-loopback API endpoints require HTTPS to protect the bearer token")
    if parsed_base.username or parsed_base.password or parsed_base.query or parsed_base.fragment:
        ap.error("--base-url must not contain credentials, query parameters, or a fragment")
    if parsed_base.path not in ("", "/"):
        ap.error("--base-url must not contain a path")
    try:
        parsed_base.port
    except ValueError:
        ap.error("--base-url contains an invalid port")
    if args.dry_run == "false":
        if not args.accept_effect:
            ap.error("--accept-effect is required when --dry-run=false")

    payload_b64 = ""
    remote_evidence_b64 = ""
    expected = args.expected_sha256 or ""
    if args.payload_file:
        p = Path(args.payload_file)
        try:
            payload = read_regular_file(p, max_bytes=700 * 1024)
        except OSError as exc:
            ap.error(f"payload file cannot be read: {exc}")
        payload_b64 = base64.b64encode(payload).decode("ascii")
        expected = expected or hashlib.sha256(payload).hexdigest()
    if args.remote_evidence_file:
        evidence_path = Path(args.remote_evidence_file)
        try:
            evidence = read_regular_file(evidence_path, max_bytes=192 * 1024)
        except OSError as exc:
            ap.error(f"remote evidence file cannot be read: {exc}")
        try:
            evidence_document = json.loads(evidence.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            ap.error(f"remote evidence must be a UTF-8 JSON document: {exc}")
        if not isinstance(evidence_document, dict):
            ap.error("remote evidence JSON must be an object")
        remote_evidence_b64 = base64.b64encode(evidence).decode("ascii")

    if (
        parsed_base.hostname == "api.github.com"
        and len(payload_b64) > MAX_GITHUB_DISPATCH_PAYLOAD_B64_CHARS
    ):
        ap.error(
            "GitHub dispatch payload exceeds the bounded 48 KiB transport budget; "
            "use a content-addressed artifact or repository reference"
        )

    inputs = {
        "operation": args.operation,
        "artifact_id": args.artifact_id,
        "payload_b64": payload_b64,
        "expected_sha256": expected,
        "dry_run": args.dry_run,
        "request_id": args.request_id,
        "effect_accepted": args.accept_effect,
        "remote_evidence_b64": remote_evidence_b64,
    }
    if args.dispatch_kind == "workflow":
        body = {"ref": args.ref, "inputs": inputs}
        dispatch_path = "actions/workflows/qikvrt_mesh_api.yml/dispatches"
    else:
        body = {"event_type": "qikvrt_mesh_api", "client_payload": inputs}
        dispatch_path = "dispatches"
    encoded_body = json.dumps(body).encode("utf-8")
    if len(encoded_body) > 1024 * 1024:
        ap.error("encoded JSON request exceeds the 1 MiB transport limit")
    url = f"{args.base_url.rstrip('/')}/repos/{args.owner}/{args.repo}/{dispatch_path}"
    req = urllib.request.Request(url, data=encoded_body, headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}, method="POST")
    opener = urllib.request.build_opener(NoRedirectHandler())
    try:
        with opener.open(req, timeout=10) as resp:
            response_text = read_response(resp)
            status = getattr(resp, "status", None)
            if status is None:
                status = resp.getcode()
            if status == 204:
                if response_text:
                    raise ValueError("204 workflow dispatch response must be empty")
                print(json.dumps(github_dispatch_transport_receipt(args), sort_keys=True))
                return 20
            print(response_text)
            parsed = json.loads(response_text)
            effect_state = parsed.get("handler_result", {}).get("effect_state")
            if effect_state == "EFFECT_ACK_DONE":
                return 0
            if effect_state == "EFFECT_ACK_CONTINUE":
                return 20
            return 1
    except urllib.error.HTTPError as exc:
        try:
            print(read_response(exc), file=sys.stderr)
        except (UnicodeDecodeError, ValueError) as response_exc:
            print(f"BLOCK API returned an unreadable error response: {response_exc}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"BLOCK API request failed: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
