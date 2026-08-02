#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Reproduce the H5 kernel, syntax, artifact and fixity checks fail-closed."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from xml.etree import ElementTree


ROOT = pathlib.Path(__file__).resolve().parent
LEAN_SOURCE = ROOT / "VRTCore_SMG_PlanckBridge.lean"
AXIOM_SOURCE = ROOT / "VRTCore_SMG_AxiomAudit.lean"
EXPECTED_AXIOM_COUNTS = {
    (): 17,
    ("propext",): 13,
    ("propext", "Quot.sound"): 2,
}


class VerificationError(RuntimeError):
    """A declared H5 verification condition failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def run(
    command: list[str],
    *,
    env: dict[str, str] | None = None,
    cwd: pathlib.Path = ROOT,
) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if process.returncode != 0:
        raise VerificationError(
            f"command failed ({process.returncode}): {' '.join(command)}\n"
            f"{process.stdout}"
        )
    return process


def check_source_shape() -> None:
    lean_text = LEAN_SOURCE.read_text(encoding="utf-8")
    audit_text = AXIOM_SOURCE.read_text(encoding="utf-8")
    require(len(re.findall(r"(?m)^theorem\s+", lean_text)) == 32,
            "Lean source must contain exactly 32 named theorems")
    require(len(re.findall(r"(?m)^#print axioms\s+", audit_text)) == 32,
            "axiom audit must contain exactly 32 directives")
    combined = lean_text + "\n" + audit_text
    forbidden = {
        "project axiom": r"(?m)^\s*axiom\b",
        "unsafe declaration": r"(?m)^\s*unsafe\b",
        "sorry/admit tactic": (
            r"(?m)^\s*(?:sorry|admit)\b|:=\s*(?:sorry|admit)\b|"
            r"\bby\s+(?:sorry|admit)\b"
        ),
    }
    for label, pattern in forbidden.items():
        require(re.search(pattern, combined) is None, f"forbidden {label} found")


def parse_axiom_output(output: str) -> dict[str, tuple[str, ...]]:
    result: dict[str, tuple[str, ...]] = {}
    no_axioms = re.compile(r"^'([^']+)' does not depend on any axioms$")
    with_axioms = re.compile(r"^'([^']+)' depends on axioms: \[(.*)\]$")
    for line in output.splitlines():
        match = no_axioms.match(line)
        if match:
            result[match.group(1)] = ()
            continue
        match = with_axioms.match(line)
        if match:
            result[match.group(1)] = tuple(
                item.strip() for item in match.group(2).split(",") if item.strip()
            )
    return result


def check_lean(lean: pathlib.Path, preload: pathlib.Path | None) -> str:
    require(lean.is_file(), f"Lean executable not found: {lean}")
    environment = os.environ.copy()
    if preload is not None:
        require(preload.is_file(), f"preload shim not found: {preload}")
        environment["LD_PRELOAD"] = str(preload)
    version = run([str(lean), "--version"], env=environment).stdout.strip()
    require("version 4.19.0" in version, f"expected Lean 4.19.0, got: {version}")
    with tempfile.TemporaryDirectory(prefix="qikvrt-h5-kernel-") as temporary:
        module_dir = pathlib.Path(temporary)
        run(
            [
                str(lean),
                "-o",
                str(module_dir / "VRTCore_SMG_PlanckBridge.olean"),
                str(LEAN_SOURCE),
            ],
            env=environment,
        )
        audit_environment = environment.copy()
        inherited = audit_environment.get("LEAN_PATH", "")
        entries = [str(module_dir), str(ROOT)]
        if inherited:
            entries.append(inherited)
        audit_environment["LEAN_PATH"] = os.pathsep.join(entries)
        audit = run([str(lean), str(AXIOM_SOURCE)], env=audit_environment).stdout
    dependencies = parse_axiom_output(audit)
    require(len(dependencies) == 32, "axiom output did not bind all 32 theorems")
    counts: dict[tuple[str, ...], int] = {}
    for axioms in dependencies.values():
        counts[axioms] = counts.get(axioms, 0) + 1
    require(counts == EXPECTED_AXIOM_COUNTS,
            f"unexpected axiom dependency counts: {counts}")
    return version


def check_syntax_and_artifacts() -> None:
    sys.path.insert(0, str(ROOT))
    from validate_h5_instance import parse_document  # pylint: disable=import-outside-toplevel

    reference = (ROOT / "H5_REFERENCE_INSTANCE.vrt").read_text(encoding="utf-8")
    document = parse_document(reference)
    require(document["effect-state"] == "EFFECT_ACK_CONTINUE",
            "reference effect state is not fail-closed")
    require(len(document["open"]) == 3, "reference must preserve three OPEN blocks")
    run([sys.executable, "-B", "-m", "unittest", "-v", "test_validate_h5_instance.py"])

    for filename in ("CLAIM_MATRIX.json", "SOURCE_EVIDENCE_BINDINGS.json", "MANIFEST.json"):
        json.loads((ROOT / filename).read_text(encoding="utf-8"))
    ElementTree.parse(ROOT / "VRTCore_SMG_EBNF_Map_DE.svg")

    pdfinfo = shutil.which("pdfinfo")
    pdftotext = shutil.which("pdftotext")
    require(pdfinfo is not None and pdftotext is not None,
            "pdfinfo and pdftotext are required")
    pdf = ROOT / "QIK-VRT_SMG_Fachartikel_DE_2026-08-02.pdf"
    info = run([pdfinfo, str(pdf)]).stdout
    require(re.search(r"(?m)^Pages:\s+11\s*$", info) is not None,
            "PDF must have exactly 11 pages")
    require("595.28 x 841.89 pts (A4)" in info, "PDF must be A4")
    with tempfile.TemporaryDirectory(prefix="qikvrt-h5-pdf-") as temporary:
        extracted = pathlib.Path(temporary) / "article.txt"
        run([pdftotext, str(pdf), str(extracted)])
        text = extracted.read_text(encoding="utf-8")
    require("�" not in text, "PDF text contains Unicode replacement characters")
    require("KERNEL_ACCEPTED_32_OF_32" in text, "PDF lacks formal status binding")
    require("OPEN_CANDIDATE" in text, "PDF lacks physical OPEN boundary")


def check_sha256sums() -> int:
    checksum_file = ROOT / "SHA256SUMS"
    entries = 0
    seen: set[str] = set()
    for number, line in enumerate(checksum_file.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\n]+)", line)
        require(match is not None, f"malformed SHA256SUMS line {number}")
        expected, relative = match.groups()
        path = pathlib.PurePosixPath(relative)
        require(not path.is_absolute() and ".." not in path.parts,
                f"unsafe checksum path: {relative}")
        require(relative not in seen, f"duplicate checksum path: {relative}")
        seen.add(relative)
        target = ROOT / relative
        require(target.is_file(), f"checksummed file missing: {relative}")
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        require(actual == expected, f"checksum mismatch: {relative}")
        entries += 1
    require(entries >= 18, "checksum inventory is unexpectedly small")
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--lean",
        type=pathlib.Path,
        default=pathlib.Path(os.environ["QIKVRT_LEAN"]) if "QIKVRT_LEAN" in os.environ else None,
        help="path to the Lean 4.19.0 executable (or set QIKVRT_LEAN)",
    )
    parser.add_argument(
        "--preload",
        type=pathlib.Path,
        default=None,
        help="optional local compatibility library supplied through LD_PRELOAD",
    )
    arguments = parser.parse_args()
    if arguments.lean is None:
        discovered = shutil.which("lean")
        require(discovered is not None, "supply --lean or QIKVRT_LEAN")
        arguments.lean = pathlib.Path(discovered)

    check_source_shape()
    version = check_lean(arguments.lean, arguments.preload)
    check_syntax_and_artifacts()
    entries = check_sha256sums()
    print(
        json.dumps(
            {
                "result": "PASS",
                "scope": "QIK-VRT VRTCore SMG H5 local formal package",
                "lean": version,
                "theorems": "32/32",
                "axioms": {"none": 17, "propext": 13, "propext+Quot.sound": 2},
                "tests": "11/11",
                "sha256_entries": entries,
                "massive_closure_current_candidate": False,
                "physical_unification": "OPEN_CANDIDATE",
                "effect_state": "EFFECT_ACK_CONTINUE",
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerificationError as error:
        print(f"BLOCK: {error}", file=sys.stderr)
        raise SystemExit(1) from error

