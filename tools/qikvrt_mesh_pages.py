#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Deterministic QIK-VRT Authority Mesh Pages projection and reobservation."""
from __future__ import annotations

import argparse
import hashlib
import html
import http.server
import json
import pathlib
import re
import threading
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[1]
REGISTRY_RELATIVE = pathlib.PurePosixPath("registry/NODEMESH_INDEX.json")
DOCS_ROOT = ROOT / "docs"
MESH_ROOT = DOCS_ROOT / "mesh"
AUTHORITY_REPOSITORY = "Goldkelch/qik-vrt"
SITE_BASE = "https://goldkelch.github.io/qik-vrt/"
MESH_URL = urllib.parse.urljoin(SITE_BASE, "mesh/")
TOPOLOGY_SCHEMA = "QIKVRT_MESH_PAGES_TOPOLOGY_V1"
LOCAL_SCHEMA = "QIKVRT_MESH_PAGES_LOCAL_SYSTEMTEST_RECEIPT_V1"
PAGES_SCHEMA = "QIKVRT_MESH_PAGES_REOBSERVATION_RECEIPT_V1"
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _is_active(node: Mapping[str, Any]) -> bool:
    return (
        node.get("registry_status") == "ACCEPTED"
        and node.get("policy_status") == "ACTIVE"
        and node.get("effective_status") == "ACTIVE"
    )


def _registry(root: pathlib.Path = ROOT) -> tuple[dict[str, Any], bytes]:
    raw = (root / REGISTRY_RELATIVE).read_bytes()
    try:
        value = json.loads(raw.decode())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid registry JSON: {exc}") from exc
    if not isinstance(value, dict) or value.get("seed_repository") != AUTHORITY_REPOSITORY:
        raise ValueError("registry is not bound to the Authority repository")
    nodes = value.get("nodes")
    if not isinstance(nodes, list) or value.get("node_count") != len(nodes):
        raise ValueError("registry node list/count drift")
    guids: set[str] = set()
    repositories: set[str] = set()
    active_count = 0
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise ValueError(f"registry node {index} must be an object")
        guid = node.get("guid")
        repository = node.get("repository")
        branch = node.get("node_branch")
        try:
            canonical_guid = str(uuid.UUID(str(guid)))
        except ValueError as exc:
            raise ValueError(f"registry node {index} GUID is invalid") from exc
        if guid != canonical_guid or guid in guids:
            raise ValueError(f"registry node {index} GUID is non-canonical or duplicate")
        if not isinstance(repository, str) or not REPOSITORY_RE.fullmatch(repository):
            raise ValueError(f"registry node {index} repository is invalid")
        if repository in repositories:
            raise ValueError(f"duplicate registry repository: {repository}")
        if not isinstance(branch, str) or not branch or any(c.isspace() for c in branch):
            raise ValueError(f"registry node {index} branch is invalid")
        guids.add(guid)
        repositories.add(repository)
        active_count += int(_is_active(node))
    if value.get("active_count") != active_count:
        raise ValueError("registry active_count drift")
    return value, raw


def topology_projection(registry: Mapping[str, Any], raw: bytes) -> dict[str, Any]:
    nodes = []
    for source in registry["nodes"]:
        if not _is_active(source):
            continue
        guid = source["guid"]
        nodes.append(
            {
                "guid": guid,
                "repository": source["repository"],
                "branch": source["node_branch"],
                "registry_status": source["registry_status"],
                "policy_status": source["policy_status"],
                "effective_status": source["effective_status"],
                "canonical_url": urllib.parse.urljoin(MESH_URL, f"nodes/{guid}/"),
            }
        )
    nodes.sort(key=lambda node: node["guid"])
    return {
        "_license": {
            "copyright": "Copyright 2026 Ingolf Lohmann.",
            "license": "PolyForm-Noncommercial-1.0.0",
        },
        "schema": TOPOLOGY_SCHEMA,
        "authority": {
            "repository": AUTHORITY_REPOSITORY,
            "canonical_url": MESH_URL,
            "role": "AUTHORITY",
        },
        "registry": {
            "path": REGISTRY_RELATIVE.as_posix(),
            "sha256": _sha256(raw),
            "qikvrt_event": registry.get("qikvrt_event"),
            "generated_utc": registry.get("generated_utc"),
            "active_count": len(nodes),
        },
        "nodes": nodes,
        "transport": {
            "mode": "EVENT_DRIVEN_ONLY",
            "local_adapters": ["BroadcastChannel", "window.postMessage"],
            "optional_stream": "SSE_EFFECT_STREAM",
            "periodic_polling": False,
        },
        "boundaries": {
            "source_present_is_not_effective_on_main": True,
            "effective_on_main_is_not_pages_deployed": True,
            "pages_deployed_is_not_browser_reobserved": True,
            "transport_ack_is_not_effect_ack": True,
            "browser_observation_is_not_effect_ack_done": True,
            "authority_main_is_not_mirror_main": True,
        },
    }


def _node_html(node: Mapping[str, str], registry_sha256: str) -> bytes:
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="canonical" href="{html.escape(node['canonical_url'])}"><title>QIK-VRT Node {html.escape(node['guid'])}</title><style>body{{margin:0;background:#0c0f14;color:#e8edf5;font:16px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace;padding:28px}}a{{color:#9ecbff}}code{{word-break:break-all}}.box{{max-width:900px;border:1px solid #303746;border-radius:12px;padding:22px;background:#151a22}}</style></head>
<body><div class="box"><h1>QIK-VRT REGISTERED MESH NODE</h1><p>Repository: <strong>{html.escape(node['repository'])}</strong></p><p>GUID: <code>{html.escape(node['guid'])}</code></p><p>Branch: <code>{html.escape(node['branch'])}</code></p><p>Registry status: <code>{node['registry_status']}</code></p><p>Policy status: <code>{node['policy_status']}</code></p><p>Effective status: <code>{node['effective_status']}</code></p><p>Registry SHA-256: <code>{registry_sha256}</code></p><p><a href="../../">Return to Authority Mesh terminal</a></p><p>This identity page is a registry projection. It does not claim synchronization, browser Effect-Acknowledgement, physical execution, independent review, <code>PASS</code>, <code>FINAL_PASS</code>, or general <code>EFFECT_ACK_DONE</code>.</p></div></body></html>
'''.encode()


def expected_files(root: pathlib.Path = ROOT) -> dict[pathlib.Path, bytes]:
    registry, raw = _registry(root)
    topology = topology_projection(registry, raw)
    files = {pathlib.Path("docs/mesh/topology.json"): _json_bytes(topology)}
    for node in topology["nodes"]:
        relative = pathlib.Path("docs/mesh/nodes") / node["guid"] / "index.html"
        files[relative] = _node_html(node, topology["registry"]["sha256"])
    return files


def _validate_shell(root: pathlib.Path) -> None:
    shell = (root / "docs/mesh/index.html").read_text()
    required = (MESH_URL, "topology.json", "BroadcastChannel", "window.addEventListener", "EventSource")
    if any(token not in shell for token in required):
        raise RuntimeError("Authority Mesh shell contract drift")
    if any(token in shell for token in ("setInterval(", "setTimeout(", "location.reload(")):
        raise RuntimeError("periodic browser work is forbidden")


def build(root: pathlib.Path = ROOT) -> list[str]:
    changed = []
    for relative, content in expected_files(root).items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_bytes() != content:
            target.write_bytes(content)
            changed.append(relative.as_posix())
    return changed


def check(root: pathlib.Path = ROOT) -> None:
    _validate_shell(root)
    expected = expected_files(root)
    errors = []
    for relative, content in expected.items():
        target = root / relative
        if not target.is_file():
            errors.append(f"missing {relative}")
        elif target.read_bytes() != content:
            errors.append(f"drift {relative}")
    expected_guids = {path.parent.name for path in expected if path.parts[:3] == ("docs", "mesh", "nodes")}
    nodes_root = root / "docs/mesh/nodes"
    if nodes_root.exists():
        for child in nodes_root.iterdir():
            try:
                canonical = str(uuid.UUID(child.name)) == child.name
            except ValueError:
                canonical = False
            if child.is_dir() and canonical and child.name not in expected_guids:
                errors.append(f"stale GUID page {child.name}")
    if errors:
        raise RuntimeError("mesh pages projection drift: " + "; ".join(errors))


def _topology(root: pathlib.Path) -> tuple[dict[str, Any], bytes]:
    registry, raw = _registry(root)
    return topology_projection(registry, raw), raw


def _routes(topology: Mapping[str, Any]) -> list[str]:
    return ["mesh/", "mesh/topology.json", *[f"mesh/nodes/{n['guid']}/" for n in topology["nodes"]]]


def _observe(base_url: str, topology: Mapping[str, Any], timeout: float) -> tuple[list[dict[str, Any]], dict[str, bytes]]:
    observations = []
    bodies = {}
    for relative in _routes(topology):
        url = urllib.parse.urljoin(base_url, relative)
        request = urllib.request.Request(url, headers={"User-Agent": "QIKVRT-Mesh-Pages-Reobserver/1"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            status = int(response.status)
            content_type = response.headers.get("Content-Type", "")
        if status != 200 or not body:
            raise RuntimeError(f"route not reobserved: {url} status={status}")
        observations.append({"relative": relative, "url": url, "status": status, "bytes": len(body), "sha256": _sha256(body), "content_type": content_type})
        bodies[relative] = body
    return observations, bodies


def _validate_bodies(topology: Mapping[str, Any], observations: Sequence[Mapping[str, Any]], bodies: Mapping[str, bytes]) -> None:
    required = set(_routes(topology))
    if {item["relative"] for item in observations} != required or set(bodies) != required:
        raise RuntimeError("observed route set differs from registry projection")
    if json.loads(bodies["mesh/topology.json"].decode()) != topology:
        raise RuntimeError("published topology differs from registry projection")
    if MESH_URL not in bodies["mesh/"].decode():
        raise RuntimeError("Authority root canonical URL missing")
    for node in topology["nodes"]:
        body = bodies[f"mesh/nodes/{node['guid']}/"].decode()
        if node["guid"] not in body or node["repository"] not in body:
            raise RuntimeError(f"GUID route identity mismatch: {node['guid']}")


def local_system_test(root: pathlib.Path = ROOT, output: pathlib.Path | None = None) -> dict[str, Any]:
    check(root)
    topology, raw = _topology(root)
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=str(root / "docs"), **kw)  # noqa: E731
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        observations, bodies = _observe(f"http://127.0.0.1:{server.server_port}/", topology, 5.0)
        _validate_bodies(topology, observations, bodies)
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5.0)
    receipt = {
        "schema": LOCAL_SCHEMA,
        "registry_sha256": _sha256(raw),
        "network_scope": "LOOPBACK_HTTP_ONLY",
        "route_count": len(observations),
        "routes": observations,
        "system_test_executed": True,
        "all_routes_reobserved": True,
        "github_pages_reachability_observed": False,
        "browser_rendering_observed": False,
        "browser_javascript_observed": False,
        "external_effect": "NONE",
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }
    if output:
        output.parent.mkdir(parents=True, exist_ok=True); output.write_bytes(_json_bytes(receipt))
    return receipt


def pages_reobserve(*, root: pathlib.Path, site_base_url: str, exact_head: str, exact_tree: str, run_id: int, event: str, output: pathlib.Path, allow_http_loopback: bool = False) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(site_base_url)
    if allow_http_loopback:
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
            raise ValueError("HTTP is allowed only for explicit loopback testing")
    elif parsed.scheme != "https" or parsed.netloc != "goldkelch.github.io" or event != "page_build":
        raise ValueError("productive reobservation requires canonical HTTPS and page_build")
    if not SHA1_RE.fullmatch(exact_head) or not SHA1_RE.fullmatch(exact_tree):
        raise ValueError("exact head/tree must be lowercase Git SHA-1")
    check(root)
    topology, raw = _topology(root)
    observations, bodies = _observe(site_base_url, topology, 15.0)
    _validate_bodies(topology, observations, bodies)
    receipt = {
        "schema": PAGES_SCHEMA,
        "repository": AUTHORITY_REPOSITORY,
        "event": event,
        "exact_head": exact_head,
        "exact_tree": exact_tree,
        "run_id": run_id,
        "observed_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "site_base_url": site_base_url,
        "registry_sha256": _sha256(raw),
        "route_count": len(observations),
        "routes": observations,
        "page_build_event_observed": event == "page_build",
        "github_pages_reachability_observed": not allow_http_loopback,
        "authority_mesh_root_observed": True,
        "machine_topology_observed": True,
        "all_active_guid_urls_observed": True,
        "single_attempt_per_route": True,
        "periodic_polling": False,
        "browser_rendering_observed": False,
        "browser_javascript_observed": False,
        "general_internet_reachability_claimed": False,
        "external_mutation": "NONE",
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True); output.write_bytes(_json_bytes(receipt))
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=ROOT)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("build"); commands.add_parser("check")
    system = commands.add_parser("system-test"); system.add_argument("--output", type=pathlib.Path)
    observe = commands.add_parser("reobserve")
    for name in ("site-base-url", "exact-head", "exact-tree", "event", "output"):
        observe.add_argument(f"--{name}", required=True)
    observe.add_argument("--run-id", required=True, type=int)
    observe.add_argument("--allow-http-loopback", action="store_true")
    args = parser.parse_args(argv); root = args.root.resolve()
    if args.command == "build":
        print(json.dumps({"changed": build(root)}, sort_keys=True))
    elif args.command == "check":
        check(root); print("QIKVRT_MESH_PAGES_PROJECTION=VERIFIED")
    elif args.command == "system-test":
        print(json.dumps(local_system_test(root, args.output), sort_keys=True))
    else:
        print(json.dumps(pages_reobserve(root=root, site_base_url=args.site_base_url, exact_head=args.exact_head, exact_tree=args.exact_tree, run_id=args.run_id, event=args.event, output=pathlib.Path(args.output), allow_http_loopback=args.allow_http_loopback), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
