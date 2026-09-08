#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Compose the verified V2 M68000 profile into the public runtime receipt.

This does not create a new external effect.  It only reconciles two local
receipts that have already been produced by the same container startup:

* the inherited V1 runtime receipt, and
* the exact-bound repository C90/M68000 execution receipt.

The resulting runtime receipt keeps every global completion boundary false and
keeps external packet I/O explicitly Linux/OCI-backed.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import tempfile
import time
from typing import Any

RUNTIME_SCHEMA = "qikvrt_cloud_transputer_runtime_v1"
M68K_SCHEMA = "qikvrt_personal_posix_m68000_tcpip_receipt_v1"
OVERLAY_SCHEMA = "qikvrt_cloud_transputer_runtime_v2_overlay_v1"
PROFILE = "QIKVRT_PERSONAL_POSIX_C90_V1"
PACKET_SCOPE = "IPV4_TCP_UDP_PACKET_ENGINE_WITH_TCP_HTTP_BOOTSTRAP_V1"
ADAPTER = "LINUX_OCI_HOST_ADAPTER"


def _require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def validate_m68k_receipt(receipt: dict[str, Any]) -> None:
    _require(receipt.get("schema") == M68K_SCHEMA, "wrong M68000 receipt schema")
    _require(receipt.get("profile") == PROFILE, "wrong personal POSIX profile")
    _require(receipt.get("m68000_machine_execution_observed") is True, "M68000 execution not observed")
    _require(receipt.get("posix_profile_selftest") == "PASS", "personal POSIX profile selftest not successful")
    _require(receipt.get("standalone_tcp_ip_scope") == PACKET_SCOPE, "wrong TCP/IP packet-engine scope")
    _require(receipt.get("standalone_tcp_ip_packet_engine") == "PASS", "TCP/IP packet engine not successful")
    _require(receipt.get("existing_effect_ack_core_linked") is True, "EFFECT_ACK core not linked")
    _require(receipt.get("effect_ack_done_local_selftest") is True, "local EFFECT_ACK positive selftest absent")
    _require(receipt.get("negative_effect_ack_fail_closed") is True, "negative EFFECT_ACK fail-closed proof absent")
    _require(receipt.get("external_packet_io_adapter") == ADAPTER, "external packet adapter boundary drift")
    _require(receipt.get("bare_metal_nic_driver_claimed") is False, "bare-metal NIC claim is forbidden")
    _require(receipt.get("full_posix_1_conformance_claimed") is False, "full POSIX.1 claim is forbidden")
    _require(receipt.get("physical_m68000_execution_claimed") is False, "physical M68000 claim is forbidden")
    _require(receipt.get("repository_or_publication_effect_claimed") is False, "repository/publication effect claim is forbidden")
    _require(receipt.get("pass") is False, "PASS must remain false")
    _require(receipt.get("final_pass") is False, "FINAL_PASS must remain false")
    _require(receipt.get("global_effect_ack_done") is False, "global EFFECT_ACK_DONE must remain false")
    for key in ("source_sha256", "m68000_binary_sha256"):
        digest = receipt.get(key)
        _require(isinstance(digest, str) and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest), f"invalid {key}")


def compose(runtime: dict[str, Any], receipt: dict[str, Any], *, observed_at_unix: int | None = None) -> dict[str, Any]:
    validate_m68k_receipt(receipt)
    _require(runtime.get("schema") == RUNTIME_SCHEMA, "wrong inherited runtime schema")
    _require(runtime.get("effect_ack_done") is False, "inherited runtime global EFFECT_ACK_DONE must be false")
    _require(runtime.get("pass") is False, "inherited runtime PASS must be false")
    _require(runtime.get("final_pass") is False, "inherited runtime FINAL_PASS must be false")
    _require(runtime.get("external_effect_claimed") is False, "inherited runtime external effect claim must be false")
    _require(runtime.get("standalone_m68000_tcp_ip_stack_claimed") is False, "full standalone M68000 TCP/IP stack claim must remain false")
    _require(runtime.get("kernel_backed_posix_tcp_ip") is True, "Linux/OCI external network adapter boundary missing")

    value = dict(runtime)
    value.update(
        {
            "runtime_overlay_schema": OVERLAY_SCHEMA,
            "personal_posix_state": "REPOSITORY_C90_M68000_PROFILE_VERIFIED",
            "personal_posix_authority": "REPOSITORY_EXACT_BOUND_IMPLEMENTATION",
            "personal_posix_profile": PROFILE,
            "personal_posix_source_sha256": receipt["source_sha256"],
            "personal_posix_m68000_binary_sha256": receipt["m68000_binary_sha256"],
            "personal_posix_m68000_machine_execution_observed": True,
            "standalone_m68000_tcp_ip_packet_engine_verified": True,
            "standalone_m68000_tcp_ip_packet_engine_scope": PACKET_SCOPE,
            "external_packet_io_adapter": ADAPTER,
            "bare_metal_nic_driver_claimed": False,
            "full_posix_1_conformance_claimed": False,
            "physical_m68000_execution_claimed": False,
            "runtime_v2_overlay_observed_at_unix": int(time.time()) if observed_at_unix is None else int(observed_at_unix),
            # Re-state terminal boundaries after composition.  Local M68000 and
            # SQL selftests are not repository, deployment, publication, or
            # global QIK-VRT completion effects.
            "external_effect_claimed": False,
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
            "standalone_m68000_tcp_ip_stack_claimed": False,
            "kernel_backed_posix_tcp_ip": True,
        }
    )
    return value


def _read_object(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _write_atomic(path: pathlib.Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        # The nginx worker must be able to read the replacement immediately at
        # the atomic rename boundary.  mkstemp defaults to 0600, so preserving
        # readability must happen before os.replace(), not as a later chmod.
        os.fchmod(fd, 0o644)
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--m68k-receipt", required=True)
    parser.add_argument("--output", action="append", required=True, help="repeat for every runtime receipt location")
    args = parser.parse_args()

    runtime = _read_object(pathlib.Path(args.runtime))
    receipt = _read_object(pathlib.Path(args.m68k_receipt))
    value = compose(runtime, receipt)
    for output in args.output:
        _write_atomic(pathlib.Path(output), value)
    print(json.dumps({
        "schema": OVERLAY_SCHEMA,
        "runtime_id": value.get("runtime_id"),
        "personal_posix_state": value["personal_posix_state"],
        "m68000_binary_sha256": value["personal_posix_m68000_binary_sha256"],
        "external_packet_io_adapter": value["external_packet_io_adapter"],
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
