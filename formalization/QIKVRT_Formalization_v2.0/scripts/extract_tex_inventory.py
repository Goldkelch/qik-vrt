#!/usr/bin/env python3
"""Extract a deterministic, raw-byte-anchored inventory of the locked TeX."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from verify_source_lock import DEFAULT_PROVENANCE, verify_source_lock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENVIRONMENTS = PROJECT_ROOT / "claims" / "TEX_ENVIRONMENTS.json"
DEFAULT_MATRIX = PROJECT_ROOT / "claims" / "APPENDIX_MATRIX.json"
DEFAULT_GRAPH = PROJECT_ROOT / "claims" / "CLAIM_GRAPH.json"

FORMAL_TYPES = ("definition", "satz", "lemma", "korollar", "proposition")
THEOREM_TYPES = ("satz", "lemma", "korollar", "proposition")
INVENTORY_TYPES = FORMAL_TYPES + ("bemerkung",)
EXPECTED_COUNTS = {
    "definitions": 20,
    "theoremLike": 20,
    "formal": 40,
    "remarks": 5,
    "proofBlocks": 17,
    "matrixRows": 34,
}

# Forward SyncTeX mapping from the locked TeX line to the physical page of a
# clean 62-page rebuild.  This is navigation metadata; raw source-span hashes
# remain the normative anchors.
PHYSICAL_PDF_PAGE_BY_LINE: dict[int, int] = {
    403: 8, 423: 9, 441: 9, 459: 9, 474: 9, 485: 10, 491: 10,
    507: 10, 517: 10, 524: 10, 532: 10, 540: 10, 568: 10,
    586: 11, 601: 11, 609: 11, 652: 12, 666: 12, 672: 12,
    687: 12, 693: 12, 731: 13, 738: 13, 767: 13, 780: 13,
    800: 14, 838: 14, 869: 15, 881: 15, 900: 15, 908: 15,
    927: 15, 946: 16, 959: 16, 979: 16, 993: 16, 1010: 16,
    1026: 17, 1052: 17, 1064: 17, 1078: 17, 1101: 18,
    1109: 18, 1129: 18, 1169: 19, 1200: 19, 1219: 19,
    1233: 19, 1244: 20, 1483: 23, 1490: 23, 1560: 24,
    1566: 24, 1622: 25, 2199: 34, 2205: 34, 2213: 34,
    2305: 36, 2672: 42, 2683: 42, 2703: 42, 3143: 49,
    3469: 53, 3470: 53, 3471: 53, 3472: 53, 3473: 53,
    3474: 54, 3475: 54, 3476: 54, 3477: 54, 3478: 54,
    3479: 54, 3480: 54, 3481: 54, 3482: 54, 3483: 54,
    3484: 54, 3485: 54, 3486: 54, 3487: 54, 3488: 54,
    3489: 54, 3490: 55, 3491: 55, 3492: 55, 3493: 55,
    3494: 55, 3495: 55, 3496: 55, 3497: 55, 3498: 55,
    3499: 55, 3500: 55, 3501: 55, 3502: 55,
}

# Source-line keyed IDs make the mapping reviewable.  The source lock makes these
# line numbers immutable for this formalization version.
CLAIMS_BY_START_LINE: dict[int, list[str]] = {
    403: ["DEF-001"],
    423: ["DEF-002"],
    441: ["SET-001"],
    474: ["DEF-003"],
    485: ["ESC-004"],
    507: ["ESC-005"],
    517: ["DEF-004"],
    524: ["ESC-003"],
    568: ["DEF-005"],
    586: ["DEF-006"],
    601: ["MAP-001"],
    652: ["DEF-007"],
    666: ["QUA-004"],
    687: ["QUA-005"],
    731: ["QUA-003", "QUA-003A"],
    767: ["SET-003"],
    780: ["MAP-003"],
    838: ["DEF-008"],
    869: ["DEF-009"],
    881: ["DEF-010"],
    900: ["GAT-003"],
    946: ["DEF-011"],
    959: ["DEF-012"],
    979: ["GAT-004"],
    1010: ["GAT-005", "GAT-006"],
    1064: ["GAT-007"],
    1101: ["RET-011"],
    1129: ["DEF-013"],
    1169: ["DEF-014"],
    1200: ["DEF-015"],
    1219: ["DEF-016"],
    1233: ["GAT-002"],
    1483: ["DIM-006", "DIM-006A"],
    1560: ["DIM-007", "DIM-007A"],
    2199: ["DEF-017"],
    2205: ["DEF-018"],
    2213: ["DEF-019"],
    2672: ["RET-011"],
    2703: ["RET-011"],
    3143: ["DEF-020"],
}

CLAIM_METADATA: dict[str, dict[str, Any]] = {
    "SET-001": {
        "statement": "The relative class and its relative complement form a complete disjoint partition.",
        "category": "MATHEMATICAL",
        "dependencies": ["DEF-002"],
    },
    "ESC-004": {
        "statement": "For the quadratic complex iteration, modulus greater than two is an escape certificate.",
        "category": "MATHEMATICAL",
        "dependencies": ["DEF-001"],
    },
    "ESC-005": {
        "statement": "The escape-radius criterion characterizes the exterior by a finite escape witness.",
        "category": "MATHEMATICAL",
        "dependencies": ["ESC-004"],
    },
    "ESC-003": {
        "statement": "The union of all finite escape stages reconstructs the complement.",
        "category": "MATHEMATICAL",
        "dependencies": ["DEF-003", "DEF-004", "ESC-004"],
    },
    "MAP-001": {
        "statement": "A correspondence map pulls the complement partition back to its domain.",
        "category": "CONDITIONAL",
        "dependencies": ["DEF-005", "DEF-006", "SET-001"],
    },
    "QUA-004": {
        "statement": "Bounded subsets of Euclidean space are finitely epsilon-quantizable.",
        "category": "MATHEMATICAL",
        "dependencies": ["DEF-007"],
    },
    "QUA-005": {
        "statement": "Bounded subsets of finite-dimensional normed spaces are finitely epsilon-quantizable.",
        "category": "MATHEMATICAL",
        "dependencies": ["QUA-004"],
    },
    "QUA-003": {
        "statement": "Finite epsilon-quantizability does not imply ontic discreteness.",
        "category": "MATHEMATICAL",
        "dependencies": ["DEF-007"],
    },
    "QUA-003A": {
        "statement": (
            "Finite exact prefix codes do not injectively determine an underlying "
            "infinite bit stream."
        ),
        "category": "MATHEMATICAL",
        "dependencies": ["DEF-007"],
    },
    "SET-003": {
        "statement": "The complement partition is independent of ambient dimension.",
        "category": "MATHEMATICAL",
        "dependencies": ["DEF-002"],
    },
    "MAP-003": {
        "statement": (
            "Image-complement inclusion always holds; equality is equivalent to "
            "disjoint image classes, follows from injectivity, and becomes the full "
            "codomain complement under bijectivity."
        ),
        "category": "MATHEMATICAL",
        "dependencies": ["DEF-002"],
    },
    "GAT-003": {
        "statement": "The exact boundedness classifier is invariant under the trajectory shift.",
        "category": "MATHEMATICAL",
        "dependencies": ["DEF-008", "DEF-009", "DEF-010"],
    },
    "GAT-004": {
        "statement": "Finite PASS/BLOCK gates are sound and refine monotonically under their certificate assumptions.",
        "category": "CONDITIONAL",
        "dependencies": ["DEF-011", "DEF-012"],
    },
    "GAT-005": {
        "statement": "The finite gate is complete for exterior states under exterior completeness.",
        "category": "CONDITIONAL",
        "dependencies": ["DEF-012", "GAT-004"],
    },
    "GAT-006": {
        "statement": "The finite gate is totally complete under exhaustive interior certificates.",
        "category": "CONDITIONAL",
        "dependencies": ["DEF-011", "DEF-012", "GAT-005"],
    },
    "GAT-007": {
        "statement": "Boundary points are instability points of the exact status classifier.",
        "category": "MATHEMATICAL",
        "dependencies": ["DEF-010", "DEF-012"],
    },
    "RET-011": {
        "statement": "Later evidence can reclassify an earlier record without overwriting an autonomous earlier state.",
        "category": "CONDITIONAL",
        "dependencies": ["DEF-008", "DEF-009", "DEF-010", "DEF-017"],
    },
    "GAT-002": {
        "statement": "Gate preservation factors through a process map exactly when status is constant on fibers.",
        "category": "MATHEMATICAL",
        "dependencies": ["DEF-014", "DEF-015", "DEF-016"],
    },
    "DIM-006": {
        "statement": "Every additive physical equation must be dimensionally homogeneous.",
        "category": "MATHEMATICAL",
        "dependencies": ["SRC-001"],
    },
    "DIM-006A": {
        "statement": (
            "Dimension-indexed and dynamically checked addition accepts equal "
            "dimensions and preserves their shared dimension."
        ),
        "category": "MATHEMATICAL",
        "dependencies": ["SRC-001"],
    },
    "DIM-007": {
        "statement": "The Lorentz interval is not a positive distance function on events.",
        "category": "MATHEMATICAL",
        "dependencies": ["SRC-001"],
    },
    "DIM-007A": {
        "statement": (
            "Integer-coordinate Minkowski witnesses violate nonnegativity and point "
            "separation for the (-+++) quadratic form."
        ),
        "category": "MATHEMATICAL",
        "dependencies": ["SRC-001"],
    },
}

FORMAL_BINDINGS: dict[str, dict[str, str]] = {
    "SET-001": {
        "batch": "Batch02-Elementary",
        "claimScope": "FULL_ENVIRONMENT",
        "module": "QIKVRTFormalization.Foundation.RelativeComplement",
        "sourcePath": "QIKVRTFormalization/Foundation/RelativeComplement.lean",
        "statementConstant": "QIKVRT.V2.Class.SET001Statement",
        "proofConstant": "QIKVRT.V2.Class.SET001_checked",
        "registryConstant": "QIKVRT.V2.Claims.SET001",
        "registrySourcePath": "QIKVRTFormalization/Claims/Batch02.lean",
    },
    "MAP-001": {
        "batch": "Batch02-Elementary",
        "claimScope": "FULL_ENVIRONMENT",
        "module": "QIKVRTFormalization.Foundation.Preimage",
        "sourcePath": "QIKVRTFormalization/Foundation/Preimage.lean",
        "statementConstant": "QIKVRT.V2.Class.MAP001Statement",
        "proofConstant": "QIKVRT.V2.Class.MAP001_checked",
        "registryConstant": "QIKVRT.V2.Claims.MAP001",
        "registrySourcePath": "QIKVRTFormalization/Claims/Batch02.lean",
    },
    "QUA-003A": {
        "batch": "Batch02-Counterexamples",
        "claimScope": "SOURCE_SUBCLAIM",
        "module": "QIKVRTFormalization.Quantization.NonDiscreteness",
        "sourcePath": "QIKVRTFormalization/Quantization/NonDiscreteness.lean",
        "statementConstant": "QIKVRT.V2.QUA003APrefixStatement",
        "proofConstant": "QIKVRT.V2.QUA003A_prefix_checked",
        "registryConstant": "QIKVRT.V2.Claims.QUA003A",
        "registrySourcePath": "QIKVRTFormalization/Claims/Batch02Counterexamples.lean",
    },
    "SET-003": {
        "batch": "Batch02-Elementary",
        "claimScope": "FULL_ENVIRONMENT",
        "module": "QIKVRTFormalization.Foundation.RelativeComplement",
        "sourcePath": "QIKVRTFormalization/Foundation/RelativeComplement.lean",
        "statementConstant": "QIKVRT.V2.Class.SET003Statement",
        "proofConstant": "QIKVRT.V2.Class.SET003_checked",
        "registryConstant": "QIKVRT.V2.Claims.SET003",
        "registrySourcePath": "QIKVRTFormalization/Claims/Batch02.lean",
    },
    "MAP-003": {
        "batch": "Batch01A",
        "claimScope": "FULL_ENVIRONMENT",
        "module": "QIKVRTFormalization.Foundation.ImageComplement",
        "sourcePath": "QIKVRTFormalization/Foundation/ImageComplement.lean",
        "statementConstant": "QIKVRT.V2.Class.MAP003Statement",
        "proofConstant": "QIKVRT.V2.Class.MAP003_checked",
        "registryConstant": "QIKVRT.V2.Claims.MAP003",
        "registrySourcePath": "QIKVRTFormalization/Claims/Batch01.lean",
    },
    "GAT-004": {
        "batch": "Batch01A",
        "claimScope": "FULL_ENVIRONMENT",
        "module": "QIKVRTFormalization.Process.Gates",
        "sourcePath": "QIKVRTFormalization/Process/Gates.lean",
        "statementConstant": "QIKVRT.V2.GAT004Statement",
        "proofConstant": "QIKVRT.V2.GAT004_checked",
        "registryConstant": "QIKVRT.V2.Claims.GAT004",
        "registrySourcePath": "QIKVRTFormalization/Claims/Batch01.lean",
    },
    "GAT-005": {
        "batch": "Batch01A",
        "claimScope": "FULL_ENVIRONMENT",
        "module": "QIKVRTFormalization.Process.GateCompleteness",
        "sourcePath": "QIKVRTFormalization/Process/GateCompleteness.lean",
        "statementConstant": "QIKVRT.V2.GAT005Statement",
        "proofConstant": "QIKVRT.V2.GAT005_checked",
        "registryConstant": "QIKVRT.V2.Claims.GAT005",
        "registrySourcePath": "QIKVRTFormalization/Claims/Batch01.lean",
    },
    "GAT-006": {
        "batch": "Batch01A",
        "claimScope": "FULL_ENVIRONMENT",
        "module": "QIKVRTFormalization.Process.GateCompleteness",
        "sourcePath": "QIKVRTFormalization/Process/GateCompleteness.lean",
        "statementConstant": "QIKVRT.V2.GAT006Statement",
        "proofConstant": "QIKVRT.V2.GAT006_checked",
        "registryConstant": "QIKVRT.V2.Claims.GAT006",
        "registrySourcePath": "QIKVRTFormalization/Claims/Batch01.lean",
    },
    "RET-011": {
        "batch": "Batch01A",
        "claimScope": "FULL_ENVIRONMENT",
        "module": "QIKVRTFormalization.Retrocausality.Reclassification",
        "sourcePath": "QIKVRTFormalization/Retrocausality/Reclassification.lean",
        "statementConstant": "QIKVRT.V2.RET011Statement",
        "proofConstant": "QIKVRT.V2.RET011_checked",
        "registryConstant": "QIKVRT.V2.Claims.RET011",
        "registrySourcePath": "QIKVRTFormalization/Claims/Batch01.lean",
    },
    "GAT-002": {
        "batch": "Batch02-Factorization",
        "claimScope": "FULL_ENVIRONMENT",
        "module": "QIKVRTFormalization.Process.Factorization",
        "sourcePath": "QIKVRTFormalization/Process/Factorization.lean",
        "statementConstant": "QIKVRT.V2.GAT002Statement",
        "proofConstant": "QIKVRT.V2.GAT002_checked",
        "registryConstant": "QIKVRT.V2.Claims.GAT002",
        "registrySourcePath": "QIKVRTFormalization/Claims/Batch02Factorization.lean",
    },
    "DIM-006A": {
        "batch": "Batch02-Dimensions",
        "claimScope": "SOURCE_SUBCLAIM",
        "module": "QIKVRTFormalization.Physics.Dimensions",
        "sourcePath": "QIKVRTFormalization/Physics/Dimensions.lean",
        "statementConstant": "QIKVRT.V2.DIM006AAdditiveStatement",
        "proofConstant": "QIKVRT.V2.DIM006A_additive_checked",
        "registryConstant": "QIKVRT.V2.Claims.DIM006A",
        "registrySourcePath": "QIKVRTFormalization/Claims/Batch02Dimensions.lean",
    },
    "DIM-007A": {
        "batch": "Batch02-Counterexamples",
        "claimScope": "SOURCE_SUBCLAIM",
        "module": "QIKVRTFormalization.Physics.Lorentz",
        "sourcePath": "QIKVRTFormalization/Physics/Lorentz.lean",
        "statementConstant": "QIKVRT.V2.DIM007ACountermodelStatement",
        "proofConstant": "QIKVRT.V2.DIM007A_countermodel_checked",
        "registryConstant": "QIKVRT.V2.Claims.DIM007A",
        "registrySourcePath": "QIKVRTFormalization/Claims/Batch02Counterexamples.lean",
    },
}

# Classification is explicit rather than guessed from words such as "falsch".
# The same surface status can belong to a mathematical counterexample, a rejected
# interpretation, or an empirical non-result.
MATRIX_CLASSIFICATIONS: list[tuple[str, str]] = [
    ("MATHEMATICAL", "PROVED"),
    ("MATHEMATICAL", "PROVED"),
    ("MATHEMATICAL", "PROVED"),
    ("CONDITIONAL", "PROVED_CONDITIONAL"),
    ("MATHEMATICAL", "REFUTED"),
    ("MATHEMATICAL", "REFUTED"),
    ("CONDITIONAL", "REFUTED_IN_MODEL"),
    ("INTERPRETIVE", "REJECTED_INFERENCE"),
    ("INTERPRETIVE", "REJECTED_INFERENCE"),
    ("EMPIRICAL", "UNSUPPORTED"),
    ("BACKGROUND", "REFUTED_BY_STANDARD_MODEL"),
    ("INTERPRETIVE", "REJECTED_INFERENCE"),
    ("CONDITIONAL", "FALSE_IN_GENERAL"),
    ("CONDITIONAL", "REFUTED_IN_MODEL"),
    ("EMPIRICAL", "OPEN"),
    ("CONDITIONAL", "PROVED_CONDITIONAL"),
    ("MATHEMATICAL", "FALSE_IN_GENERAL"),
    ("MATHEMATICAL", "PROVED"),
    ("MATHEMATICAL", "REFUTED_BY_COUNTERMODEL"),
    ("MATHEMATICAL", "PROVED"),
    ("MATHEMATICAL", "FALSE_IN_GENERAL"),
    ("BACKGROUND", "ESTABLISHED"),
    ("BACKGROUND", "FALSE_IN_CLASSICAL_THEORY"),
    ("EMPIRICAL", "OPEN"),
    ("INTERPRETIVE", "REJECTED_INFERENCE"),
    ("MATHEMATICAL", "REFUTED"),
    ("EMPIRICAL", "HYPOTHESIS"),
    ("BACKGROUND", "ESTABLISHED"),
    ("EMPIRICAL", "UNESTABLISHED"),
    ("INTERPRETIVE", "UNDEFINED_AS_STATED"),
    ("EMPIRICAL", "HYPOTHESIS"),
    ("INTERPRETIVE", "ARGUMENT"),
    ("INTERPRETIVE", "INTERPRETATION"),
    ("NORMATIVE", "NORMATIVE_CONCLUSION"),
]

MATRIX_RELATED_CLAIMS: dict[int, list[str]] = {
    1: ["SET-001"],
    2: ["ESC-003", "ESC-004"],
    3: ["GAT-003"],
    4: ["GAT-004", "GAT-005", "GAT-006"],
    5: ["GAT-005", "GAT-006"],
    7: ["RET-011"],
    14: ["RET-011"],
    16: ["GAT-002"],
    17: ["GAT-005"],
    18: ["QUA-004"],
    19: ["QUA-003"],
    20: ["SET-003"],
    21: ["MAP-003"],
    25: ["DIM-006"],
    26: ["DIM-007"],
    30: ["GAT-003"],
    33: ["DEF-020"],
}


def raw_span(lines: list[bytes], start_line: int, end_line: int) -> dict[str, Any]:
    payload = b"".join(lines[start_line - 1 : end_line])
    physical_page = PHYSICAL_PDF_PAGE_BY_LINE.get(start_line)
    if physical_page is None:
        raise ValueError(f"missing physical PDF page mapping for line {start_line}")
    return {
        "id": f"SPAN-TEX-{start_line:04d}-{end_line:04d}",
        "startLine": start_line,
        "endLine": end_line,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "hashMode": "raw-bytes-inclusive-lines-v1",
        "physicalPdfPage": physical_page,
        "pageMappingMethod": "synctex-forward-clean-rebuild-v1",
    }


def _extract_blocks(text_lines: list[str], types: tuple[str, ...]) -> list[dict[str, Any]]:
    type_pattern = "|".join(re.escape(item) for item in types)
    begin_re = re.compile(
        rf"^\\begin\{{(?P<type>{type_pattern})\}}(?:\[(?P<title>.*)\])?\s*$"
    )
    end_re = re.compile(rf"^\\end\{{(?P<type>{type_pattern})\}}\s*$")
    stack: list[tuple[str, int, str | None]] = []
    blocks: list[dict[str, Any]] = []
    for line_no, line in enumerate(text_lines, 1):
        begin = begin_re.match(line)
        if begin:
            stack.append((begin.group("type"), line_no, begin.group("title")))
            continue
        end = end_re.match(line)
        if end:
            if not stack:
                raise ValueError(f"unmatched end of {end.group('type')} at line {line_no}")
            env_type, start_line, title = stack.pop()
            if env_type != end.group("type"):
                raise ValueError(
                    f"environment mismatch: {env_type} at {start_line}, "
                    f"{end.group('type')} at {line_no}"
                )
            blocks.append(
                {
                    "type": env_type,
                    "titleTex": title,
                    "startLine": start_line,
                    "endLine": line_no,
                }
            )
    if stack:
        raise ValueError(f"unclosed environments: {stack}")
    return sorted(blocks, key=lambda block: block["startLine"])


def extract_environments(tex_bytes: bytes, source_hash: str) -> dict[str, Any]:
    raw_lines = tex_bytes.splitlines(keepends=True)
    text_lines = [line.decode("utf-8").rstrip("\r\n") for line in raw_lines]
    blocks = _extract_blocks(text_lines, INVENTORY_TYPES)
    proof_blocks = _extract_blocks(text_lines, ("proof",))

    counters: defaultdict[str, int] = defaultdict(int)
    environments: list[dict[str, Any]] = []
    theorem_envs: list[dict[str, Any]] = []
    for block in blocks:
        if block["type"] == "definition":
            group = "definition"
            prefix = "DEF"
        elif block["type"] == "bemerkung":
            group = "remark"
            prefix = "REM"
        else:
            group = "theoremLike"
            prefix = "THM"
        counters[group] += 1
        env_id = f"ENV-{prefix}-{counters[group]:03d}"
        labels: list[str] = []
        for line in text_lines[block["startLine"] - 1 : block["endLine"]]:
            labels.extend(re.findall(r"\\label\{([^}]+)\}", line))
        claim_ids = CLAIMS_BY_START_LINE.get(block["startLine"], [])
        environment = {
            "id": env_id,
            "ordinalWithinGroup": counters[group],
            "environmentType": block["type"],
            "group": group,
            "formal": group != "remark",
            "titleTex": block["titleTex"],
            "labels": labels,
            "claimIds": claim_ids,
            "sourceSpan": raw_span(raw_lines, block["startLine"], block["endLine"]),
            "proofBlockIds": [],
        }
        environments.append(environment)
        if group == "theoremLike":
            theorem_envs.append(environment)

    proof_records: list[dict[str, Any]] = []
    assigned: set[str] = set()
    for index, block in enumerate(proof_blocks, 1):
        candidates = [
            environment
            for environment in theorem_envs
            if environment["sourceSpan"]["endLine"] < block["startLine"]
            and environment["id"] not in assigned
        ]
        if not candidates:
            raise ValueError(f"proof at line {block['startLine']} has no theorem-like predecessor")
        associated = max(candidates, key=lambda item: item["sourceSpan"]["endLine"])
        assigned.add(associated["id"])
        proof_id = f"PROOF-{index:03d}"
        associated["proofBlockIds"].append(proof_id)
        proof_records.append(
            {
                "id": proof_id,
                "associatedEnvironmentId": associated["id"],
                "sourceSpan": raw_span(raw_lines, block["startLine"], block["endLine"]),
            }
        )

    counts = {
        "definitions": counters["definition"],
        "theoremLike": counters["theoremLike"],
        "formal": counters["definition"] + counters["theoremLike"],
        "remarks": counters["remark"],
        "proofBlocks": len(proof_records),
    }
    for key in ("definitions", "theoremLike", "formal", "remarks", "proofBlocks"):
        if counts[key] != EXPECTED_COUNTS[key]:
            raise ValueError(f"{key}: expected {EXPECTED_COUNTS[key]}, got {counts[key]}")
    formal_starts = {
        environment["sourceSpan"]["startLine"]
        for environment in environments
        if environment["formal"]
    }
    if formal_starts != set(CLAIMS_BY_START_LINE):
        missing = sorted(formal_starts - set(CLAIMS_BY_START_LINE))
        stale = sorted(set(CLAIMS_BY_START_LINE) - formal_starts)
        raise ValueError(f"formal mapping mismatch; missing={missing}, stale={stale}")

    return {
        "schemaVersion": "2.0.0",
        "sourceSha256": source_hash,
        "lineSpanConvention": {
            "numbering": "one-based",
            "end": "inclusive",
            "bytes": "exact source bytes including line terminators",
            "algorithm": "SHA-256",
        },
        "counts": counts,
        "environments": environments,
        "proofBlocks": proof_records,
    }


def extract_matrix(tex_bytes: bytes, source_hash: str) -> dict[str, Any]:
    raw_lines = tex_bytes.splitlines(keepends=True)
    text_lines = [line.decode("utf-8").rstrip("\r\n") for line in raw_lines]
    section_line = next(
        index
        for index, line in enumerate(text_lines, 1)
        if line == r"\section{Anspruchs- und Beweismatrix}"
    )
    rows: list[tuple[int, list[str]]] = []
    for line_no in range(section_line + 1, len(text_lines) + 1):
        line = text_lines[line_no - 1]
        if line == r"\bottomrule":
            break
        stripped = line.strip()
        if " & " not in stripped or not stripped.endswith(r"\\"):
            continue
        if stripped.startswith(r"\textbf{Aussage}"):
            continue
        fields = stripped[:-2].rstrip().rsplit(" & ", 2)
        if len(fields) != 3:
            raise ValueError(f"cannot split appendix matrix row at line {line_no}")
        rows.append((line_no, fields))

    if len(rows) != EXPECTED_COUNTS["matrixRows"]:
        raise ValueError(
            f"matrixRows: expected {EXPECTED_COUNTS['matrixRows']}, got {len(rows)}"
        )
    if len(MATRIX_CLASSIFICATIONS) != len(rows):
        raise ValueError("classification table does not cover every appendix row")

    records: list[dict[str, Any]] = []
    for index, ((line_no, fields), classification) in enumerate(
        zip(rows, MATRIX_CLASSIFICATIONS, strict=True), 1
    ):
        category, disposition = classification
        records.append(
            {
                "id": f"MATRIX-{index:03d}",
                "statementTex": fields[0],
                "manuscriptStatusTex": fields[1],
                "rationaleTex": fields[2],
                "epistemicCategory": category,
                "truthDisposition": disposition,
                "machineProofBindingAllowed": category in {"MATHEMATICAL", "CONDITIONAL"},
                "relatedClaimIds": MATRIX_RELATED_CLAIMS.get(index, []),
                "sourceSpan": raw_span(raw_lines, line_no, line_no),
            }
        )
    return {
        "schemaVersion": "2.0.0",
        "sourceSha256": source_hash,
        "counts": {"rows": len(records)},
        "rows": records,
    }


def build_claim_graph(environment_data: dict[str, Any]) -> dict[str, Any]:
    reverse: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for environment in environment_data["environments"]:
        for claim_id in environment["claimIds"]:
            reverse[claim_id].append(environment)

    nodes: list[dict[str, Any]] = [
        {
            "id": "SRC-001",
            "statement": "The formalization is anchored to the immutable TeX source bytes.",
            "epistemicCategory": "SOURCE",
            "formalizationStatus": "LOCKED",
            "dependencies": [],
            "environmentIds": [],
            "sourceSpanIds": [],
            "proofBlockIds": [],
            "formalBinding": None,
        }
    ]

    for index in range(1, 21):
        claim_id = f"DEF-{index:03d}"
        envs = reverse[claim_id]
        if len(envs) != 1:
            raise ValueError(f"{claim_id} must map to exactly one definition environment")
        title = envs[0]["titleTex"] or claim_id
        nodes.append(
            {
                "id": claim_id,
                "statement": f"Manuscript definition: {title}",
                "epistemicCategory": "DEFINITION",
                "formalizationStatus": "PENDING",
                "dependencies": ["SRC-001"],
                "environmentIds": [envs[0]["id"]],
                "sourceSpanIds": [envs[0]["sourceSpan"]["id"]],
                "proofBlockIds": [],
                "formalBinding": None,
            }
        )

    for claim_id, metadata in CLAIM_METADATA.items():
        envs = reverse[claim_id]
        if not envs:
            raise ValueError(f"{claim_id} is not mapped to a formal environment")
        binding = FORMAL_BINDINGS.get(claim_id)
        formal_binding = None
        status = "PENDING"
        if binding is not None:
            status = "KERNEL_CHECKED"
            lean_source = PROJECT_ROOT / binding["sourcePath"]
            registry_source = PROJECT_ROOT / binding["registrySourcePath"]
            formal_binding = {
                "proofSystem": "Lean4",
                "bindingStrength": "STRONG",
                **binding,
                "leanSourceSha256": hashlib.sha256(lean_source.read_bytes()).hexdigest(),
                "registrySourceSha256": hashlib.sha256(
                    registry_source.read_bytes()
                ).hexdigest(),
            }
        nodes.append(
            {
                "id": claim_id,
                "statement": metadata["statement"],
                "epistemicCategory": metadata["category"],
                "formalizationStatus": status,
                "dependencies": metadata["dependencies"],
                "environmentIds": [environment["id"] for environment in envs],
                "sourceSpanIds": [environment["sourceSpan"]["id"] for environment in envs],
                "proofBlockIds": [
                    proof_id
                    for environment in envs
                    for proof_id in environment["proofBlockIds"]
                ],
                "formalBinding": formal_binding,
            }
        )

    return {
        "schemaVersion": "2.0.0",
        "sourceNodeId": "SRC-001",
        "policy": {
            "proofForbiddenCategories": ["EMPIRICAL", "INTERPRETIVE", "NORMATIVE"],
            "unconditionalCategory": "MATHEMATICAL",
            "conditionalCategory": "CONDITIONAL",
            "pendingIsRequiredWithoutKernelBinding": True,
            "bindingScopes": {
                "FULL_ENVIRONMENT": "aggregate source claim discharged",
                "SOURCE_SUBCLAIM": "checked atom only; aggregate parent remains pending",
            },
        },
        "counts": {
            "nodes": len(nodes),
            "definitionNodes": sum(
                node["epistemicCategory"] == "DEFINITION" for node in nodes
            ),
            "kernelCheckedClaims": sum(
                node["formalizationStatus"] == "KERNEL_CHECKED" for node in nodes
            ),
            "pendingNodes": sum(node["formalizationStatus"] == "PENDING" for node in nodes),
        },
        "nodes": nodes,
    }


def _canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _write_or_check(path: Path, data: dict[str, Any], check: bool) -> bool:
    expected = _canonical_json(data)
    if check:
        try:
            actual = path.read_text(encoding="utf-8")
        except OSError:
            print(f"ERROR: missing generated file {path}", file=sys.stderr)
            return False
        if actual != expected:
            print(f"ERROR: generated file is stale: {path}", file=sys.stderr)
            return False
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(expected, encoding="utf-8")
    return True


def generate(provenance_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    source_errors = verify_source_lock(provenance_path)
    if source_errors:
        raise ValueError("; ".join(source_errors))
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    tex_record = provenance["sourceFiles"]["tex"]
    tex_path = (provenance_path.parent / tex_record["path"]).resolve()
    tex_bytes = tex_path.read_bytes()
    environments = extract_environments(tex_bytes, tex_record["sha256"])
    matrix = extract_matrix(tex_bytes, tex_record["sha256"])
    graph = build_claim_graph(environments)
    return environments, matrix, graph


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provenance", type=Path, default=DEFAULT_PROVENANCE)
    parser.add_argument("--environments", type=Path, default=DEFAULT_ENVIRONMENTS)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--graph", type=Path, default=DEFAULT_GRAPH)
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare committed JSON with a fresh extraction instead of writing",
    )
    args = parser.parse_args(argv)
    try:
        environments, matrix, graph = generate(args.provenance.resolve())
    except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    results = [
        _write_or_check(args.environments, environments, args.check),
        _write_or_check(args.matrix, matrix, args.check),
        _write_or_check(args.graph, graph, args.check),
    ]
    if not all(results):
        return 1
    action = "verified" if args.check else "wrote"
    print(
        f"PASS {action}: 20 definitions, 20 theorem-like environments, "
        f"5 remarks, 17 proof blocks, 34 matrix rows"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
