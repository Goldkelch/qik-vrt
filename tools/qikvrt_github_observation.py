#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Read-only GitHub transport with lossless, freshly revalidated observations.

This is transport, not review authority. Every mutable read reaches GitHub.
An HTTP 304 can reuse only the exact digest-checked response that supplied its
validator. Errors never return cached data. No token rotation or blind retry.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request
import uuid


class ObservationError(RuntimeError):
    def __init__(self, message, *, status=None):
        super().__init__(message)
        self.status = status


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ObservationError("GITHUB_OBSERVATION_REDIRECT_REJECTED")


class ObservationClient:
    """One explicit repository/read lane, with an append-only receipt journal."""

    def __init__(self, repository: str, token: str, root: Path, *,
                 lane: str = "ROLE_LOCAL", opener=None, clock=time.time):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ObservationError("GITHUB_OBSERVATION_REPOSITORY_INVALID")
        if not token:
            raise ObservationError("GITHUB_OBSERVATION_CREDENTIAL_MISSING")
        if lane not in {"ROLE_LOCAL", "MESH_READ_ONLY"}:
            raise ObservationError("GITHUB_OBSERVATION_LANE_INVALID")
        self.repository, self.token, self.root, self.lane = repository, token, Path(root), lane
        self.opener = opener or urllib.request.build_opener(_NoRedirect()).open
        self.clock = clock
        for part in ("objects", "index", "receipts"):
            (self.root / part).mkdir(parents=True, exist_ok=True)

    def _url(self, path: str) -> str:
        url = path if path.startswith("https://") else "https://api.github.com/" + path
        parsed = urllib.parse.urlsplit(url)
        if (parsed.scheme != "https" or parsed.netloc != "api.github.com"
                or parsed.fragment or parsed.username or parsed.password
                or not parsed.path.startswith(f"/repos/{self.repository}/")
                or any(part in {".", ".."} for part in parsed.path.split("/"))
                or "%" in parsed.path):
            raise ObservationError("GITHUB_OBSERVATION_ENDPOINT_OUTSIDE_BOUND_REPOSITORY")
        return url

    def _object(self, data: bytes) -> str:
        digest = _digest(data)
        path = self.root / "objects" / digest
        try:
            with path.open("xb") as stream:
                stream.write(data)
        except FileExistsError:
            if path.read_bytes() != data:
                raise ObservationError("GITHUB_OBSERVATION_OBJECT_CORRUPT")
        return digest

    def _receipt(self, value: dict) -> str:
        # Full bodies are content addressed. Receipts retain every 200/304/error
        # observation. The index is only a reconstructible pointer, not evidence.
        value = {"schema": "qikvrt_github_observation_v1", "repository": self.repository,
                 "lane": self.lane, "observed_at_epoch": self.clock(), **value}
        data = _canonical(value)
        path = self.root / "receipts" / (uuid.uuid4().hex + ".json")
        with path.open("xb") as stream:
            stream.write(data)
        return _digest(data)

    def _load(self, key: str, url: str) -> dict | None:
        path = self.root / "index" / (key + ".json")
        if not path.exists():
            return None
        try:
            item = json.loads(path.read_bytes())
            digest = item["body_sha256"]
            if not re.fullmatch(r"[a-f0-9]{64}", digest):
                raise ValueError("digest")
            body = (self.root / "objects" / digest).read_bytes()
            if (item["url"] != url or item["repository"] != self.repository
                    or item["lane"] != self.lane or _digest(body) != digest):
                raise ValueError("binding")
            item["body"] = body
            return item
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise ObservationError("GITHUB_OBSERVATION_CACHE_CORRUPT") from exc

    @staticmethod
    def _headers(headers) -> dict[str, str]:
        allowed = {"etag", "link", "date", "x-github-request-id", "retry-after",
                   "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset",
                   "x-ratelimit-resource"}
        return {k.lower(): str(v) for k, v in headers.items() if k.lower() in allowed}

    def get(self, path: str) -> tuple[Any, dict[str, str]]:
        url = self._url(path)
        key = _digest(_canonical([self.repository, self.lane, url]))
        prior = self._load(key, url)
        headers = {"Authorization": "Bearer " + self.token,
                   "Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28",
                   "User-Agent": "qikvrt-repository-observer"}
        validator = prior.get("etag") if prior else None
        if validator:
            headers["If-None-Match"] = validator
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with self.opener(request, timeout=30) as response:
                status, raw = response.status, response.read()
                observed_headers = self._headers(response.headers)
        except urllib.error.HTTPError as exc:
            status, raw = exc.code, exc.read()
            observed_headers = self._headers(exc.headers)
        except (OSError, urllib.error.URLError) as exc:
            self._receipt({"url": url, "status": None, "error": type(exc).__name__})
            raise ObservationError("GITHUB_OBSERVATION_TRANSPORT_UNAVAILABLE " + url) from exc

        if status not in {200, 304}:
            raw_digest = self._object(raw)
            limited = status in {403, 429} and (
                observed_headers.get("x-ratelimit-remaining") == "0"
                or b"rate limit" in raw.lower() or "retry-after" in observed_headers)
            blocker = ("GITHUB_INSTALLATION_RATE_LIMIT_EXHAUSTED" if limited
                       else "GITHUB_OBSERVATION_HTTP_ERROR")
            self._receipt({"url": url, "status": status, "headers": observed_headers,
                           "body_sha256": raw_digest, "first_blocker": blocker,
                           "cached_body_used": False})
            raise ObservationError(f"{blocker} status={status} endpoint={url} "
                                   f"reset={observed_headers.get('x-ratelimit-reset', 'UNKNOWN')} "
                                   f"retry_after={observed_headers.get('retry-after', 'UNKNOWN')}", status=status)

        if status == 304:
            if (prior is None or not validator
                    or observed_headers.get("etag", validator) != validator):
                raise ObservationError("GITHUB_OBSERVATION_304_BINDING_INVALID")
            raw = prior["body"]
            # 304 may omit entity headers. Retain their exact previous values.
            effective = {**prior.get("headers", {}), **observed_headers}
        else:
            effective = observed_headers
        try:
            value = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._receipt({"url": url, "status": status, "headers": observed_headers,
                           "body_sha256": self._object(raw), "first_blocker": "INVALID_JSON"})
            raise ObservationError("GITHUB_OBSERVATION_INVALID_JSON") from exc
        digest = self._object(raw)
        self._receipt({"url": url, "status": status, "headers": observed_headers,
                       "body_sha256": digest, "request_validator": validator,
                       "prior_body_sha256": prior.get("body_sha256") if prior else None,
                       "fresh_server_validation": True})
        index = {"repository": self.repository, "lane": self.lane, "url": url,
                 "body_sha256": digest, "etag": effective.get("etag"), "headers": effective}
        target = self.root / "index" / (key + ".json")
        temporary = target.with_name(target.name + "." + uuid.uuid4().hex + ".tmp")
        temporary.write_bytes(_canonical(index))
        temporary.replace(target)
        return value, effective

    def pages(self, path: str) -> list[Any]:
        pages, seen = [], set()
        next_url: str | None = self._url(path)
        while next_url is not None:
            if next_url in seen or len(seen) >= 1000:
                raise ObservationError("GITHUB_OBSERVATION_PAGINATION_NOT_COMPLETE")
            seen.add(next_url)
            value, headers = self.get(next_url)
            pages.append(value)
            links = re.findall(r'<([^>]+)>;\s*rel="next"', headers.get("link", ""))
            if len(links) > 1:
                raise ObservationError("GITHUB_OBSERVATION_PAGINATION_AMBIGUOUS")
            next_url = self._url(links[0]) if links else None
        return pages


def environment_client(repository: str | None = None) -> ObservationClient:
    # The lane is chosen before work. A rate-limit response never rotates tokens.
    mesh = os.environ.get("QIKVRT_REVIEW_READ_TOKEN", "")
    return ObservationClient(
        os.environ.get("REPOSITORY", os.environ.get("GITHUB_REPOSITORY", "")) or repository or "",
        mesh or os.environ.get("GH_TOKEN", ""),
        Path(os.environ.get("QIKVRT_OBSERVATION_ROOT", ".qikvrt/github-observations")),
        lane="MESH_READ_ONLY" if mesh else "ROLE_LOCAL",
    )


def gh_read_json(command) -> Any:
    """Recognize only the executor's existing REST GET forms; reject mutations."""
    if list(command[:2]) != ["gh", "api"]:
        raise ObservationError("GITHUB_OBSERVATION_COMMAND_INVALID")
    args = list(command[2:])
    paginated = args[:2] == ["--paginate", "--slurp"]
    if paginated:
        args = args[2:]
    if len(args) != 1:
        raise ObservationError("GITHUB_OBSERVATION_READ_ONLY_COMMAND_REQUIRED")
    match = re.match(r"^(?:https://api.github.com/)?repos/([^/]+/[^/]+)/", args[0])
    client = environment_client(match.group(1) if match else None)
    return client.pages(args[0]) if paginated else client.get(args[0])[0]
