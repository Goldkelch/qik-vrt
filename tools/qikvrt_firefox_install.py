#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Install the QIK-VRT Firefox adapter only after explicit license acceptance."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path

ACCEPTANCE_PHRASE = "I ACCEPT QIK-VRT NONCOMMERCIAL TERMS"
SOFTWARE_LICENSE = "PolyForm-Noncommercial-1.0.0"
DOCUMENTATION_LICENSE = "CC-BY-NC-ND-4.0"
REQUIRED_LICENSE_MEMBERS = (
    "licenses/PolyForm-Noncommercial-1.0.0.txt",
    "licenses/CC-BY-NC-ND-4.0.txt",
    "licenses/QIKVRT-LICENSE-GUIDE.md",
    "licenses/QIKVRT-COMMERCIAL-USE-POLICY.md",
)


class LicenseNotAccepted(RuntimeError):
    pass


def _bundle(xpi: Path) -> tuple[dict, dict[str, str]]:
    if xpi.is_symlink() or not xpi.is_file():
        raise ValueError(f"XPI must be a regular file: {xpi}")
    with zipfile.ZipFile(xpi) as archive:
        names = set(archive.namelist())
        missing = sorted(set(REQUIRED_LICENSE_MEMBERS) - names)
        if missing:
            raise ValueError(f"XPI lacks required license payloads: {missing}")
        manifest = json.loads(archive.read("manifest.json"))
        terms = {
            name: archive.read(name).decode("utf-8")
            for name in REQUIRED_LICENSE_MEMBERS
        }
    extension_id = manifest.get("browser_specific_settings", {}).get("gecko", {}).get("id")
    if not extension_id or "/" in extension_id or "\\" in extension_id:
        raise ValueError("Firefox extension id is missing or unsafe")
    return {"manifest": manifest, "extension_id": extension_id}, terms


def render_notice() -> str:
    return """QIK-VRT INSTALLATION TERMS

Current QIK-VRT-controlled software is licensed, where identified, under
PolyForm-Noncommercial-1.0.0. Free private/personal use is included only to the
extent permitted by the full standard license. Ordinary commercial use is not
licensed; anticipated commercial use requires a separate written license from
the rights holder unless another applicable right or exception applies.

QIK-VRT documentation/non-source material identified as such is governed by
CC-BY-NC-ND-4.0. Earlier or specifically identified grants and all third-party
components remain governed by their own applicable terms.

Why this acceptance gate exists: installation creates a concrete local copy and
operational use. The gate makes the applicable noncommercial boundary visible
before the installer mutates the Firefox profile and prevents repository access,
a successful build, or technical execution from being mistaken for a commercial
license grant. It does not waive statutory exceptions or alter earlier valid
grants.

The exact legal texts and project licensing guide are embedded in this XPI.
"""


def _print_full_terms(terms: dict[str, str]) -> None:
    for name in REQUIRED_LICENSE_MEMBERS:
        print(f"\n===== {name} =====\n")
        print(terms[name])


def require_acceptance(explicit: bool) -> None:
    print(render_notice(), file=sys.stderr)
    if explicit:
        return
    if not sys.stdin.isatty():
        raise LicenseNotAccepted(
            "explicit license acceptance is required; rerun interactively or use --accept-license"
        )
    answer = input(f'Type exactly "{ACCEPTANCE_PHRASE}" to continue: ').strip()
    if answer != ACCEPTANCE_PHRASE:
        raise LicenseNotAccepted("license terms were not accepted")


def install(xpi: Path, profile: Path, *, accepted: bool) -> dict:
    bundle, _terms = _bundle(xpi)
    if not accepted:
        raise LicenseNotAccepted("license terms were not accepted")
    if profile.exists() and profile.is_symlink():
        raise ValueError("Firefox profile must not be a symlink")
    profile.mkdir(parents=True, exist_ok=True)
    extensions = profile / "extensions"
    if extensions.exists() and extensions.is_symlink():
        raise ValueError("Firefox extensions directory must not be a symlink")
    extensions.mkdir(parents=True, exist_ok=True)

    data = xpi.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    target = extensions / f"{bundle['extension_id']}.xpi"
    temp = extensions / f".{bundle['extension_id']}.{os.getpid()}.tmp"
    try:
        with temp.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, target)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass
    if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        raise RuntimeError("installed XPI hash differs from accepted artifact")
    return {
        "schema": "qikvrt_firefox_license_acceptance_install_v1",
        "installed": True,
        "path": str(target),
        "extension_id": bundle["extension_id"],
        "sha256": digest,
        "accepted_license": SOFTWARE_LICENSE,
        "documentation_license": DOCUMENTATION_LICENSE,
        "commercial_use_licensed": False,
        "activation_claimed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xpi", type=Path, required=True)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--accept-license", action="store_true")
    parser.add_argument("--show-licenses", action="store_true")
    args = parser.parse_args(argv)
    try:
        _bundle_meta, terms = _bundle(args.xpi)
        if args.show_licenses:
            print(render_notice())
            _print_full_terms(terms)
            if args.profile is None:
                return 0
        if args.profile is None:
            parser.error("--profile is required for installation")
        require_acceptance(args.accept_license)
        result = install(args.xpi, args.profile, accepted=True)
    except (LicenseNotAccepted, OSError, ValueError, RuntimeError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        print(f"BLOCK {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
