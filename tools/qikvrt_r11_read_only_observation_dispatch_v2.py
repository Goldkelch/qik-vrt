#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Bounded execution helper for the R11 read-only observation V2 contract."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any, NoReturn

REPOSITORY = "Goldkelch/qik-vrt"
MIRROR = "ingolf-lohmann/qik-vrt"
AUTHORITY_SOURCE_MAIN = "121f2f611eb1a7cf903ca80325d5900aad4f7876"
MIRROR_SOURCE_MAIN = "8cdf8e71fe5edbadae4d80c606c07bdeea3ed4bc"
CONTRACT = "state/authorization/r11/R11_READ_ONLY_OBSERVATION_DISPATCH_V2.json"
PREDECESSOR = "state/authorization/r11/R11_READ_ONLY_OBSERVATION_DISPATCH_V1.json"
PREDECESSOR_BLOB = "f19ea9df13afd465f3c9a32e5e6e3ee43d04a3b0"
PREDECESSOR_PR = 403
PREDECESSOR_HEAD = "6b0fd669b880505d71c0d03cb60a85d08bf0c326"
PREDECESSOR_RUN = 31021322563
PREDECESSOR_JOB = 92358456632
CARRIER_PR = 395
R11_BRANCH = "recovery-execution/vrtcore-relational-h3-e1-v1"
R11_HEAD = "26a45a0af463dcd8bb1667897d1a999230375307"
R10_HEAD = "507f4f30b694df3a415194b2c2cae41a0922b6d9"
C2_COMMIT = "376e869dc3504929b8913146cb29264d3ac585f3"
C2_BLOB = "d81135af4a14c5fa3d67966761f473569c7d2689"
C2_BYTES = 23415
C2_SHA256 = "3114f282d76e453ae0aa9106a0b7481c0be8566bd6b38674922eb3e5f0bc74f4"
TARGET_ID = 21763614
TARGET_DOI = "10.5281/zenodo.21763614"
PROXY_BRANCH = "trusted/r11-read-only-observation-proxy-v2"
PROXY_WORKFLOW = ".github/workflows/qikvrt_r11_read_only_observation_proxy_v2.yml"
RECEIPT = "receipts/anticipation/0005-r11-draft-shape-observation-receipt-pair.json"
BACKOFF = (15.0, 45.0)
MAX_RESPONSE = 2 * 1024 * 1024


def block(message: str) -> NoReturn:
    raise SystemExit("BLOCK: " + message)


def git(root: pathlib.Path, *args: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args], check=True, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout.strip()
    except subprocess.CalledProcessError as exc:
        block("Git binding failed: " + exc.stderr.strip()[:300])


def read_object(path: pathlib.Path, maximum: int = MAX_RESPONSE) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        block("JSON path is not a regular file")
    raw = path.read_bytes()
    if not raw or len(raw) > maximum:
        block("JSON bytes are empty or oversized")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        block("JSON bytes are invalid")
    if not isinstance(value, dict):
        block("JSON root is not an object")
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class RetryingGitHubAPI:
    """GET-only GitHub transport with one exact installation-rate-limit retry class."""

    def __init__(
        self,
        token: str,
        *,
        transport: Callable[[str], tuple[int, Mapping[str, str], bytes]] | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        **_ignored: Any,
    ) -> None:
        if len(token) < 20 or any(character.isspace() for character in token):
            block("GITHUB_TOKEN is missing or structurally invalid")
        self.token = token
        self.transport = transport
        self.sleeper = sleeper
        self.retry_count = 0

    @staticmethod
    def _validate_path(path: str) -> None:
        if not path.startswith("/repos/Goldkelch/qik-vrt/") or any(
            character in path for character in ("\x00", "\r", "\n", "#")
        ):
            block("GitHub GET escaped the pinned repository")
        parts = urllib.parse.urlsplit(path)
        if parts.scheme or parts.netloc or parts.fragment:
            block("GitHub GET path is not relative")
        if parts.query and not (
            parts.query == "per_page=100"
            and re.fullmatch(r"/repos/Goldkelch/qik-vrt/actions/runs/[0-9]+/jobs", parts.path)
        ):
            block("GitHub GET query escaped the exact jobs pagination allowance")

    @staticmethod
    def _rate_limited(status: int, headers: Mapping[str, str], raw: bytes) -> bool:
        if status != 403 or headers.get("x-ratelimit-remaining") != "0":
            return False
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            return False
        return isinstance(value, dict) and isinstance(value.get("message"), str) and value["message"].startswith(
            "API rate limit exceeded for installation."
        )

    def _once(self, path: str) -> tuple[int, Mapping[str, str], bytes]:
        if self.transport is not None:
            return self.transport(path)
        request = urllib.request.Request(
            "https://api.github.com" + path,
            method="GET",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer " + self.token,
                "User-Agent": "qik-vrt-r11-v2",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        opener = urllib.request.build_opener(NoRedirect())
        try:
            response: Any = opener.open(request, timeout=45)
        except urllib.error.HTTPError as exc:
            response = exc
        except (OSError, urllib.error.URLError):
            block("GitHub GET transport failed")
        try:
            status = int(response.status)
            headers = {str(k).lower(): str(v) for k, v in response.headers.items()}
            raw = response.read(MAX_RESPONSE + 1)
        finally:
            response.close()
        if len(raw) > MAX_RESPONSE:
            block("GitHub GET response exceeded its byte bound")
        return status, headers, raw

    def raw_get(self, path: str, accept: tuple[int, ...] = (200,)) -> tuple[int, Mapping[str, str], bytes]:
        self._validate_path(path)
        for attempt in range(len(BACKOFF) + 1):
            status, headers, raw = self._once(path)
            if status in accept:
                return status, headers, raw
            if self._rate_limited(status, headers, raw) and attempt < len(BACKOFF):
                self.retry_count += 1
                print(f"R11_V2_GITHUB_RATE_LIMIT_RETRY={self.retry_count}")
                self.sleeper(BACKOFF[attempt])
                continue
            block(f"GitHub GET rejected (HTTP {status})")
        block("GitHub GET retry state is unreachable")

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        accept: tuple[int, ...] = (200,),
        allow_ambiguous_transport: bool = False,
    ) -> tuple[int, dict[str, Any]]:
        if method != "GET" or payload is not None or allow_ambiguous_transport:
            block("R11 V2 GitHub transport permits GET only")
        status, _headers, raw = self.raw_get(path, accept)
        if not raw:
            return status, {}
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            block("GitHub GET returned invalid JSON")
        if not isinstance(value, dict):
            block("GitHub GET returned a non-object")
        if self.token.encode("utf-8") in raw:
            block("GitHub GET response contained its bearer credential")
        return status, value

    def download_job_log(self, job_id: int) -> bytes:
        path = f"/repos/{REPOSITORY}/actions/jobs/{job_id}/logs"
        status, headers, _raw = self.raw_get(path, (301, 302, 303, 307, 308))
        if status not in {301, 302, 303, 307, 308}:
            block("job log endpoint did not redirect")
        url = headers.get("location", "")
        opener = urllib.request.build_opener(NoRedirect())
        for _ in range(3):
            parts = urllib.parse.urlsplit(url)
            host = (parts.hostname or "").lower()
            if parts.scheme != "https" or not (
                host.endswith(".actions.githubusercontent.com")
                or host.endswith(".blob.core.windows.net")
                or host.endswith(".githubusercontent.com")
            ) or parts.username or parts.password or parts.fragment:
                block("job log redirect escaped its credential-free allowlist")
            request = urllib.request.Request(url, headers={"User-Agent": "qik-vrt-r11-v2"})
            try:
                response: Any = opener.open(request, timeout=45)
            except urllib.error.HTTPError as exc:
                response = exc
            try:
                code = int(response.status)
                if code in {301, 302, 303, 307, 308}:
                    url = urllib.parse.urljoin(url, response.headers.get("Location", ""))
                    response.read(1)
                    continue
                if code != 200:
                    block("job log download status differs")
                raw = response.read(1024 * 1024 + 1)
            finally:
                response.close()
            if len(raw) > 1024 * 1024 or self.token.encode("utf-8") in raw:
                block("job log bytes exceeded or disclosed the token")
            return raw
        block("job log redirect chain exceeded its bound")


def remote_main(root: pathlib.Path) -> str:
    output = git(root, "ls-remote", "--heads", "origin", "refs/heads/main").split()
    if len(output) < 2 or output[1] != "refs/heads/main":
        block("main ref cannot be resolved")
    return output[0]


def _assert_contract_pair(authority: pathlib.Path, mirror: pathlib.Path) -> dict[str, Any]:
    left = (authority / CONTRACT).read_bytes()
    right = (mirror / CONTRACT).read_bytes()
    if left != right or git(authority, "hash-object", CONTRACT) != git(mirror, "hash-object", CONTRACT):
        block("paired V2 contract bytes differ")
    old_left = (authority / PREDECESSOR).read_bytes()
    old_right = (mirror / PREDECESSOR).read_bytes()
    if old_left != old_right or git(authority, "hash-object", PREDECESSOR) != PREDECESSOR_BLOB:
        block("frozen predecessor contract differs")
    value = read_object(authority / CONTRACT)
    canonical = json.dumps(
        value.get("authorization_payload"), ensure_ascii=False, allow_nan=False,
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    if hashlib.sha256(canonical).hexdigest() != value.get("authorization_payload_sha256"):
        block("V2 authorization payload digest differs")
    return value


def preflight(args: argparse.Namespace) -> int:
    authority = args.authority_root.resolve()
    mirror = args.mirror_root.resolve()
    proxy = args.proxy_root.resolve()
    if git(authority, "rev-parse", "HEAD^{commit}") != args.event_base:
        block("Authority event base differs")
    if git(mirror, "rev-parse", "HEAD^{commit}") != args.mirror_main:
        block("Mirror main checkout differs")
    if remote_main(authority) != args.event_base:
        block("Authority main moved after proxy opening")
    if remote_main(mirror) != args.mirror_main:
        block("Mirror main moved during V2 binding")
    try:
        subprocess.run(["git", "-C", str(authority), "merge-base", "--is-ancestor", AUTHORITY_SOURCE_MAIN, args.event_base], check=True)
        subprocess.run(["git", "-C", str(mirror), "merge-base", "--is-ancestor", MIRROR_SOURCE_MAIN, args.mirror_main], check=True)
    except subprocess.CalledProcessError:
        block("current main does not descend from its bound V2 source")
    if git(proxy, "rev-parse", "HEAD^{commit}") != args.proxy_head:
        block("proxy head differs")
    if git(proxy, "show", "-s", "--format=%P", "HEAD") != AUTHORITY_SOURCE_MAIN:
        block("proxy is not the direct Authority-source child")
    delta = git(proxy, "diff", "--name-status", "--no-renames", AUTHORITY_SOURCE_MAIN, args.proxy_head, "--")
    if delta != "A\t" + PROXY_WORKFLOW:
        block("proxy delta is not the exact one workflow path")
    contract = _assert_contract_pair(authority, mirror)
    payload = contract["authorization_payload"]
    if payload["source_mains"] != {"authority": AUTHORITY_SOURCE_MAIN, "mirror": MIRROR_SOURCE_MAIN}:
        block("V2 source-main binding differs")
    api = RetryingGitHubAPI(os.environ.get("GITHUB_TOKEN", ""))
    _, run = api.request("GET", f"/repos/{REPOSITORY}/actions/runs/{PREDECESSOR_RUN}/attempts/1")
    _, job = api.request("GET", f"/repos/{REPOSITORY}/actions/jobs/{PREDECESSOR_JOB}")
    _, artifacts = api.request("GET", f"/repos/{REPOSITORY}/actions/runs/{PREDECESSOR_RUN}/artifacts")
    _, old_pr = api.request("GET", f"/repos/{REPOSITORY}/pulls/{PREDECESSOR_PR}")
    _, carrier = api.request("GET", f"/repos/{REPOSITORY}/pulls/{CARRIER_PR}")
    _, current = api.request("GET", f"/repos/{REPOSITORY}/pulls/{args.proxy_pr}")
    if (
        run.get("id") != PREDECESSOR_RUN or run.get("run_attempt") != 1
        or run.get("head_sha") != PREDECESSOR_HEAD or run.get("event") != "pull_request"
        or run.get("status") != "completed" or run.get("conclusion") != "failure"
    ):
        block("consumed V1 run binding differs")
    steps = {item.get("number"): item.get("conclusion") for item in job.get("steps", []) if isinstance(item, dict)}
    if job.get("id") != PREDECESSOR_JOB or job.get("run_id") != PREDECESSOR_RUN or steps.get(4) != "failure" or any(steps.get(i) != "skipped" for i in range(5, 11)):
        block("consumed V1 job boundary differs")
    if artifacts.get("total_count") != 0 or artifacts.get("artifacts") != []:
        block("consumed V1 run unexpectedly has an artifact")
    if old_pr.get("state") != "closed" or old_pr.get("merged") is True or old_pr.get("head", {}).get("sha") != PREDECESSOR_HEAD:
        block("frozen V1 proxy PR differs")
    if carrier.get("state") != "open" or carrier.get("draft") is not True or carrier.get("head", {}).get("sha") != R11_HEAD:
        block("R11 carrier PR differs")
    if current.get("state") != "open" or current.get("draft") is not True or current.get("head", {}).get("sha") != args.proxy_head or current.get("base", {}).get("sha") != args.event_base:
        block("new V2 proxy PR differs")
    decoded = api.download_job_log(PREDECESSOR_JOB).decode("utf-8-sig")
    required = (
        "GitHub GET /repos/Goldkelch/qik-vrt/git/ref/heads/main returned 403",
        "API rate limit exceeded for installation",
        "Process completed with exit code 1.",
    )
    if any(decoded.count(marker) != 1 for marker in required):
        block("V1 rate-limit log markers differ")
    if any(marker in decoded for marker in (
        "VRTCORE_H3_R11_DRAFT_SHAPE_OBSERVATION=CAPTURED",
        "R11_READ_ONLY_OBSERVATION_ARTIFACT_PERSISTED=true",
    )):
        block("V1 log crossed the no-observation boundary")
    for root in (authority, mirror):
        if (root / RECEIPT).exists():
            block("R11 receipt pair already exists")
    synthetic = {
        "ref": "refs/heads/" + R11_BRANCH, "before": R10_HEAD, "after": R11_HEAD,
        "created": False, "deleted": False, "forced": False,
        "repository": {"full_name": REPOSITORY}, "head_commit": {"id": R11_HEAD},
    }
    args.synthetic_event.write_text(json.dumps(synthetic, sort_keys=True) + "\n", encoding="utf-8")
    print(f"R11_V2_PREFLIGHT=BOUND retries={api.retry_count}")
    return 0


def observe(args: argparse.Namespace) -> int:
    mirror_root = pathlib.Path("mirror").resolve()
    mirror_checkout = git(mirror_root, "rev-parse", "HEAD^{commit}")
    if remote_main(mirror_root) != mirror_checkout:
        block("Mirror main moved before R11 observation")
    module_path = args.controller_root / "tools/qikvrt_vrtcore_h3_e1_recovery.py"
    spec = importlib.util.spec_from_file_location("qikvrt_r11_v2_controller", module_path)
    if spec is None or spec.loader is None:
        block("immutable controller import failed")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.GitHubAPI = RetryingGitHubAPI
    result = int(module.main([
        "--observe-draft-shape", "--execution-root", str(args.execution_root),
        "--observation-output", str(args.observation_output),
        "--github-output", str(args.github_output),
    ]))
    if remote_main(mirror_root) != mirror_checkout:
        block("Mirror main moved across R11 observation")
    return result


def verify(args: argparse.Namespace) -> int:
    report = read_object(args.report, maximum=64 * 1024)
    if report.get("schema") != "qikvrt_vrtcore_h3_r11_draft_shape_observation_v1" or report.get("read_only") is not True:
        block("R11 observation report identity differs")
    if report.get("request") != {
        "api_origin": "https://zenodo.org", "method": "GET",
        "path": "/api/deposit/depositions/21763614", "count": 2,
        "redirects_followed": False,
    }:
        block("R11 observation request boundary differs")
    binding = report.get("binding", {})
    if binding.get("record_id") != TARGET_ID or binding.get("doi") != TARGET_DOI or binding.get("c2_commit") != C2_COMMIT or binding.get("c2_evidence_sha256") != C2_SHA256:
        block("R11 report C2 binding differs")
    if report.get("allowlist", {}).get("raw_response_bytes_persisted") is not False or report.get("allowlist", {}).get("arbitrary_response_values_persisted") is not False:
        block("R11 report allowlist differs")
    if report.get("effect_boundary", {}).get("zenodo_mutation") is not False or report.get("effect_boundary", {}).get("terminal_result") != "OBSERVATION_RECEIPT_PERSISTED_BLOCKED":
        block("R11 report effect boundary differs")
    raw = args.checkpoint.read_bytes()
    if len(raw) != C2_BYTES or hashlib.sha256(raw).hexdigest() != C2_SHA256 or git(args.execution_root, "hash-object", str(args.checkpoint.relative_to(args.execution_root))) != C2_BLOB:
        block("unchanged C2 checkpoint differs")
    print("R11_V2_ARTIFACT_BYTES=VERIFIED")
    return 0


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    commands = value.add_subparsers(dest="command", required=True)
    p = commands.add_parser("preflight")
    p.add_argument("--authority-root", type=pathlib.Path, required=True)
    p.add_argument("--mirror-root", type=pathlib.Path, required=True)
    p.add_argument("--proxy-root", type=pathlib.Path, required=True)
    p.add_argument("--event-base", required=True)
    p.add_argument("--mirror-main", required=True)
    p.add_argument("--proxy-head", required=True)
    p.add_argument("--proxy-pr", type=int, required=True)
    p.add_argument("--synthetic-event", type=pathlib.Path, required=True)
    p.set_defaults(handler=preflight)
    p = commands.add_parser("observe")
    p.add_argument("--controller-root", type=pathlib.Path, required=True)
    p.add_argument("--execution-root", type=pathlib.Path, required=True)
    p.add_argument("--observation-output", type=pathlib.Path, required=True)
    p.add_argument("--github-output", type=pathlib.Path, required=True)
    p.set_defaults(handler=observe)
    p = commands.add_parser("verify")
    p.add_argument("--execution-root", type=pathlib.Path, required=True)
    p.add_argument("--report", type=pathlib.Path, required=True)
    p.add_argument("--checkpoint", type=pathlib.Path, required=True)
    p.set_defaults(handler=verify)
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
