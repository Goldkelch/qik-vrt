#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed reciprocal barrier for the EFFECT_ACK publication effect."""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


AUTHORITY_REPOSITORY = "Goldkelch/qik-vrt"
MIRROR_REPOSITORY = "ingolf-lohmann/qik-vrt"
FINALIZE_BRANCH = "automation/effect-ack-universality-finalize-20260722"
MARKER_PATH = "release/effect-ack-universality-request.json"
ZERO40 = "0" * 40
ZERO64 = "0" * 64

GitHubRead = Callable[[str, str], Mapping[str, Any] | None]


class BarrierError(RuntimeError):
    """The reciprocal pre-publication subject barrier is not satisfied."""


def _require(observed: Any, expected: Any, label: str) -> None:
    if observed != expected:
        raise BarrierError(f"{label} differs from the exact release subject")


def _canonical_payload_digest(marker: Mapping[str, Any]) -> str:
    projection = copy.deepcopy(dict(marker))
    projection.pop("authorization_payload_sha256", None)
    return hashlib.sha256(
        json.dumps(
            projection,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _with_payload_digest(marker: dict[str, Any]) -> dict[str, Any]:
    marker["authorization_payload_sha256"] = _canonical_payload_digest(marker)
    return marker


def _mirror_marker(
    authority_marker: Mapping[str, Any], mirror_commit: str, shared_tree: str
) -> dict[str, Any]:
    marker = copy.deepcopy(dict(authority_marker))
    marker["release"]["expected_source_commit"] = mirror_commit
    marker["release"]["expected_source_tree"] = shared_tree
    return _with_payload_digest(marker)


def _inert_marker(active_marker: Mapping[str, Any]) -> dict[str, Any]:
    marker = copy.deepcopy(dict(active_marker))
    marker["state"] = "inactive"
    marker["confirm"] = "NOT_AUTHORIZED"
    marker["release"]["expected_source_commit"] = ZERO40
    marker["release"]["expected_source_tree"] = ZERO40
    for key in ("client_sha256", "manifest_sha256", "reservation_evidence_sha256"):
        marker["zenodo"][key] = ZERO64
    marker["zenodo"]["paper_doi"] = None
    marker["zenodo"]["software_doi"] = None
    return _with_payload_digest(marker)


def _decode_content(value: Mapping[str, Any], label: str) -> bytes:
    if value.get("encoding") != "base64" or not isinstance(value.get("content"), str):
        raise BarrierError(f"{label} is not an exact base64 GitHub content object")
    try:
        return base64.b64decode("".join(value["content"].split()), validate=True)
    except (ValueError, TypeError) as error:
        raise BarrierError(f"{label} has invalid base64 bytes") from error


def _tag_object(
    api: GitHubRead,
    repository: str,
    tag: str,
    live_main: str,
    shared_tree: str,
    release: Mapping[str, Any],
    *,
    expected_object_sha: str | None = None,
) -> str:
    encoded_tag = urllib.parse.quote(tag, safe="")
    ref = api(repository, f"git/ref/tags/{encoded_tag}")
    ref_object = ref.get("object", {})
    if ref_object.get("type") != "tag" or not isinstance(ref_object.get("sha"), str):
        raise BarrierError(f"{repository} release ref is not an annotated tag")
    object_sha = ref_object["sha"]
    if expected_object_sha is not None:
        _require(object_sha, expected_object_sha, f"{repository} annotated tag object")
    tag_object = api(repository, f"git/tags/{object_sha}")
    target = tag_object.get("object", {})
    expected_tagger = {
        "name": release["tagger_name"],
        "email": release["tagger_email"],
        "date": release["tagger_timestamp"],
    }
    if (
        tag_object.get("tag") != tag
        or tag_object.get("message") != release["tag_message"]
        or tag_object.get("tagger") != expected_tagger
        or target.get("type") != "commit"
        or target.get("sha") != live_main
    ):
        raise BarrierError(
            f"{repository} annotated tag is not bound to the exact live main"
        )
    target_commit = api(repository, f"git/commits/{live_main}")
    _require(
        target_commit.get("tree", {}).get("sha"),
        shared_tree,
        f"{repository} annotated tag target tree",
    )
    return object_sha


def _authorization_marker(
    api: GitHubRead,
    repository: str,
    authorization_commit: str,
    live_main: str,
    active_marker: Mapping[str, Any],
) -> None:
    commit = api(repository, f"commits/{authorization_commit}")
    parents = commit.get("parents")
    if not isinstance(parents, list) or [item.get("sha") for item in parents] != [
        live_main
    ]:
        raise BarrierError(
            f"{repository} authorization is not a one-parent live-main successor"
        )
    files = commit.get("files")
    if not isinstance(files, list) or [
        (item.get("filename"), item.get("status")) for item in files
    ] != [(MARKER_PATH, "modified")]:
        raise BarrierError(f"{repository} authorization commit is not marker-only")

    encoded_path = urllib.parse.quote(MARKER_PATH, safe="/")
    active_query = urllib.parse.urlencode({"ref": authorization_commit})
    observed_active = json.loads(
        _decode_content(
            api(repository, f"contents/{encoded_path}?{active_query}"),
            f"{repository} active marker",
        )
    )
    _require(observed_active, active_marker, f"{repository} active marker")
    inert_query = urllib.parse.urlencode({"ref": live_main})
    observed_inert = json.loads(
        _decode_content(
            api(repository, f"contents/{encoded_path}?{inert_query}"),
            f"{repository} inert parent marker",
        )
    )
    _require(
        observed_inert,
        _inert_marker(active_marker),
        f"{repository} inert parent marker",
    )


def validate_pretag_barrier(
    *,
    marker_bytes: bytes,
    expected_marker_sha256: str,
    expected_source_commit: str,
    expected_shared_tree: str,
    github_sha: str,
    local_repository: str,
    api: GitHubRead,
) -> dict[str, Any]:
    """Require exact marker transactions and a safe local/peer pre-tag state."""

    if local_repository not in {AUTHORITY_REPOSITORY, MIRROR_REPOSITORY}:
        raise BarrierError("local repository is outside the reciprocal release contract")
    _require(
        hashlib.sha256(marker_bytes).hexdigest(),
        expected_marker_sha256,
        "local marker digest",
    )
    marker = json.loads(marker_bytes)
    if not isinstance(marker, dict):
        raise BarrierError("local marker is not a JSON object")
    _require(marker.get("state"), "finalize", "local marker state")
    _require(
        marker.get("confirm"),
        "FINALIZE_TAGS_AND_ZENODO_PUBLICATION",
        "local marker confirmation",
    )
    _require(
        marker.get("authorization_payload_sha256"),
        _canonical_payload_digest(marker),
        "local marker canonical payload digest",
    )
    release = marker.get("release")
    if not isinstance(release, dict):
        raise BarrierError("local marker release contract is absent")
    _require(
        release.get("expected_source_commit"),
        expected_source_commit,
        "local marker commit",
    )
    _require(
        release.get("expected_source_tree"),
        expected_shared_tree,
        "local marker tree",
    )
    _require(
        marker.get("repository_policy", {}).get("finalize_ref"),
        "refs/heads/" + FINALIZE_BRANCH,
        "local finalize ref",
    )

    def required(repository: str, path: str) -> Mapping[str, Any]:
        value = api(repository, path)
        if value is None:
            raise BarrierError(f"{repository} required reciprocal object is absent: {path}")
        return value

    mains: dict[str, str] = {}
    authorizations: dict[str, str] = {}
    for repository in (AUTHORITY_REPOSITORY, MIRROR_REPOSITORY):
        main = required(repository, "git/ref/heads/main").get("object", {}).get("sha")
        if not isinstance(main, str):
            raise BarrierError(f"{repository} main ref has no exact object SHA")
        _require(
            required(repository, f"git/commits/{main}").get("tree", {}).get("sha"),
            expected_shared_tree,
            f"{repository} main tree",
        )
        authorization = (
            required(repository, f"git/ref/heads/{FINALIZE_BRANCH}")
            .get("object", {})
            .get("sha")
        )
        if not isinstance(authorization, str):
            raise BarrierError(
                f"{repository} finalize authorization ref has no exact object SHA"
            )
        active = _mirror_marker(marker, main, expected_shared_tree)
        if repository == local_repository:
            _require(main, expected_source_commit, "current local main")
            _require(authorization, github_sha, "current local authorization ref")
            _require(active, marker, "local active marker")
        _authorization_marker(required, repository, authorization, main, active)
        mains[repository] = main
        authorizations[repository] = authorization

    tag = release.get("tag")
    if not isinstance(tag, str) or not tag:
        raise BarrierError("local marker tag is absent")
    tag_path = "git/ref/tags/" + urllib.parse.quote(tag, safe="")
    peer_repository = (
        MIRROR_REPOSITORY
        if local_repository == AUTHORITY_REPOSITORY
        else AUTHORITY_REPOSITORY
    )
    if api(local_repository, tag_path) is not None:
        raise BarrierError(
            f"{local_repository} local release tag already exists before local tag effect"
        )

    def peer_tag_object() -> str | None:
        if api(peer_repository, tag_path) is None:
            return None
        return _tag_object(
            required,
            peer_repository,
            tag,
            mains[peer_repository],
            expected_shared_tree,
            release,
        )

    initial_peer_tag_object = peer_tag_object()

    for repository in (AUTHORITY_REPOSITORY, MIRROR_REPOSITORY):
        _require(
            required(repository, "git/ref/heads/main").get("object", {}).get("sha"),
            mains[repository],
            f"{repository} main terminal readback",
        )
        _require(
            required(repository, f"git/ref/heads/{FINALIZE_BRANCH}")
            .get("object", {})
            .get("sha"),
            authorizations[repository],
            f"{repository} authorization terminal readback",
        )
    terminal_peer_tag_object = peer_tag_object()
    if initial_peer_tag_object is not None:
        _require(
            terminal_peer_tag_object,
            initial_peer_tag_object,
            f"{peer_repository} peer annotated tag terminal readback",
        )
    if api(local_repository, tag_path) is not None:
        raise BarrierError(
            f"{local_repository} local release tag appeared during the reciprocal barrier"
        )

    return {
        "schema": "qikvrt_effect_ack_pretag_barrier_v1",
        "state": "LOCAL_TAG_ABSENT_PEER_ABSENT_OR_EXACT_VERIFIED",
        "local_repository": local_repository,
        "local_main": mains[local_repository],
        "peer_main": mains[peer_repository],
        "peer_tag_object": terminal_peer_tag_object,
        "shared_tree": expected_shared_tree,
        "authority_authorization": authorizations[AUTHORITY_REPOSITORY],
        "mirror_authorization": authorizations[MIRROR_REPOSITORY],
    }


def validate_prepublication_barrier(
    *,
    marker_bytes: bytes,
    expected_marker_sha256: str,
    expected_authority_commit: str,
    expected_shared_tree: str,
    expected_authority_tag_object: str,
    github_sha: str,
    api: GitHubRead,
) -> dict[str, Any]:
    """Validate both exact live subjects and their separate marker transactions."""

    _require(
        hashlib.sha256(marker_bytes).hexdigest(),
        expected_marker_sha256,
        "Authority marker digest",
    )
    marker = json.loads(marker_bytes)
    if not isinstance(marker, dict):
        raise BarrierError("Authority marker is not a JSON object")
    _require(marker.get("state"), "finalize", "Authority marker state")
    _require(
        marker.get("confirm"),
        "FINALIZE_TAGS_AND_ZENODO_PUBLICATION",
        "Authority marker confirmation",
    )
    _require(
        marker.get("authorization_payload_sha256"),
        _canonical_payload_digest(marker),
        "Authority marker canonical payload digest",
    )
    release = marker.get("release")
    if not isinstance(release, dict):
        raise BarrierError("Authority marker release contract is absent")
    _require(
        release.get("expected_source_commit"),
        expected_authority_commit,
        "Authority marker commit",
    )
    _require(
        release.get("expected_source_tree"),
        expected_shared_tree,
        "Authority marker tree",
    )
    _require(
        marker.get("repository_policy", {}).get("finalize_ref"),
        "refs/heads/" + FINALIZE_BRANCH,
        "Authority finalize ref",
    )

    authority_authorization = api(
        AUTHORITY_REPOSITORY, f"git/ref/heads/{FINALIZE_BRANCH}"
    )["object"]["sha"]
    _require(
        authority_authorization,
        github_sha,
        "current Authority authorization ref",
    )
    authority_main = api(AUTHORITY_REPOSITORY, "git/ref/heads/main")["object"]["sha"]
    _require(authority_main, expected_authority_commit, "current Authority main")
    _require(
        api(AUTHORITY_REPOSITORY, f"git/commits/{authority_main}")
        .get("tree", {})
        .get("sha"),
        expected_shared_tree,
        "current Authority main tree",
    )
    _authorization_marker(
        api,
        AUTHORITY_REPOSITORY,
        authority_authorization,
        authority_main,
        marker,
    )

    mirror_main = api(MIRROR_REPOSITORY, "git/ref/heads/main")["object"]["sha"]
    _require(
        api(MIRROR_REPOSITORY, f"git/commits/{mirror_main}")
        .get("tree", {})
        .get("sha"),
        expected_shared_tree,
        "current Mirror main tree",
    )

    mirror_authorization = api(
        MIRROR_REPOSITORY, f"git/ref/heads/{FINALIZE_BRANCH}"
    )["object"]["sha"]
    mirror_marker = _mirror_marker(marker, mirror_main, expected_shared_tree)
    _authorization_marker(
        api,
        MIRROR_REPOSITORY,
        mirror_authorization,
        mirror_main,
        mirror_marker,
    )

    tag = release["tag"]
    authority_tag_object = _tag_object(
        api,
        AUTHORITY_REPOSITORY,
        tag,
        authority_main,
        expected_shared_tree,
        release,
        expected_object_sha=expected_authority_tag_object,
    )
    mirror_tag_object = _tag_object(
        api,
        MIRROR_REPOSITORY,
        tag,
        mirror_main,
        expected_shared_tree,
        release,
    )
    _require(
        api(AUTHORITY_REPOSITORY, "git/ref/heads/main")["object"]["sha"],
        authority_main,
        "Authority main terminal readback",
    )
    _require(
        api(MIRROR_REPOSITORY, "git/ref/heads/main")["object"]["sha"],
        mirror_main,
        "Mirror main terminal readback",
    )
    _require(
        api(AUTHORITY_REPOSITORY, f"git/ref/heads/{FINALIZE_BRANCH}")["object"][
            "sha"
        ],
        authority_authorization,
        "Authority authorization terminal readback",
    )
    _require(
        api(MIRROR_REPOSITORY, f"git/ref/heads/{FINALIZE_BRANCH}")["object"][
            "sha"
        ],
        mirror_authorization,
        "Mirror authorization terminal readback",
    )
    _require(
        _tag_object(
            api,
            AUTHORITY_REPOSITORY,
            tag,
            authority_main,
            expected_shared_tree,
            release,
            expected_object_sha=authority_tag_object,
        ),
        authority_tag_object,
        "Authority annotated tag terminal readback",
    )
    _require(
        _tag_object(
            api,
            MIRROR_REPOSITORY,
            tag,
            mirror_main,
            expected_shared_tree,
            release,
            expected_object_sha=mirror_tag_object,
        ),
        mirror_tag_object,
        "Mirror annotated tag terminal readback",
    )
    _require(
        api(AUTHORITY_REPOSITORY, "git/ref/heads/main")["object"]["sha"],
        authority_main,
        "Authority main final cut",
    )
    _require(
        api(MIRROR_REPOSITORY, "git/ref/heads/main")["object"]["sha"],
        mirror_main,
        "Mirror main final cut",
    )
    _require(
        api(AUTHORITY_REPOSITORY, f"git/ref/heads/{FINALIZE_BRANCH}")["object"][
            "sha"
        ],
        authority_authorization,
        "Authority authorization final cut",
    )
    _require(
        api(MIRROR_REPOSITORY, f"git/ref/heads/{FINALIZE_BRANCH}")["object"][
            "sha"
        ],
        mirror_authorization,
        "Mirror authorization final cut",
    )
    return {
        "schema": "qikvrt_effect_ack_prepublication_barrier_v1",
        "state": "EXACT_RECIPROCAL_SUBJECT_VERIFIED",
        "authority_main": authority_main,
        "mirror_main": mirror_main,
        "shared_tree": expected_shared_tree,
        "authority_authorization": authority_authorization,
        "mirror_authorization": mirror_authorization,
        "authority_tag_object": authority_tag_object,
        "mirror_tag_object": mirror_tag_object,
    }


def _github_reader(
    token: str,
    *,
    authenticated_repository: str = AUTHORITY_REPOSITORY,
    missing_ok: bool = False,
) -> GitHubRead:
    def read(repository: str, path: str) -> Mapping[str, Any] | None:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "qikvrt-effect-ack-prepublication-barrier",
        }
        if repository == authenticated_repository:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(
            f"https://api.github.com/repos/{repository}/{path}", headers=headers
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                value = json.load(response)
        except urllib.error.HTTPError as error:
            if missing_ok and error.code == 404:
                return None
            raise
        if not isinstance(value, dict):
            raise BarrierError(f"GitHub response is not an object: {repository}/{path}")
        return value

    return read


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--marker", type=Path, required=True)
    parser.add_argument("--expected-marker-sha256", required=True)
    parser.add_argument("--expected-authority-commit", required=True)
    parser.add_argument("--expected-shared-tree", required=True)
    parser.add_argument("--expected-authority-tag-object", required=True)
    parser.add_argument("--github-sha", required=True)
    arguments = parser.parse_args()
    token = os.environ.get("GH_API_TOKEN", "")
    if not token:
        raise SystemExit("BLOCK: GH_API_TOKEN is unavailable")
    try:
        evidence = validate_prepublication_barrier(
            marker_bytes=arguments.marker.read_bytes(),
            expected_marker_sha256=arguments.expected_marker_sha256,
            expected_authority_commit=arguments.expected_authority_commit,
            expected_shared_tree=arguments.expected_shared_tree,
            expected_authority_tag_object=arguments.expected_authority_tag_object,
            github_sha=arguments.github_sha,
            api=_github_reader(token),
        )
    except (BarrierError, KeyError, json.JSONDecodeError) as error:
        raise SystemExit(f"BLOCK: {error}") from error
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
