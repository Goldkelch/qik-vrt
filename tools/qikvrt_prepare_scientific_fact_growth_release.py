#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Deterministically materialize the scientific fact-growth release envelope.

This tool creates only repository-side candidate bytes.  It does not contact
Zenodo or the IETF, consume an owner authorization, or claim an external
effect.  The generated machine-proof bundle establishes mechanical
admissibility under the active v2 policy; the separate natural-person exact
authorization remains mandatory before any production mutation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from collections.abc import Mapping, Sequence
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
PUBLICATION_ID = "qikvrt-scientific-fact-growth-mesh-v1"
PUBLICATION = pathlib.PurePosixPath(
    "docs/publications/2026-08-01-scientific-fact-growth-mesh"
)
IETF_STEM = pathlib.PurePosixPath(
    "external/ietf/draft-lohmann-qikvrt-scientific-claim-assurance-00"
)
RELEASE = pathlib.PurePosixPath(
    "release/scientific-fact-growth-mesh-2026-08-01"
)
KERNEL_RECEIPT = PUBLICATION / "LEAN_KERNEL_RECEIPT.json"
CLAIM_MATRIX = PUBLICATION / "CLAIM_MATRIX.json"
RETURN_RECEIPT = PUBLICATION / "PREPUBLICATION_RETURN_RECEIPT.json"
FILESET = PUBLICATION / "ZENODO_FILESET.md"
CHECKSUMS = PUBLICATION / "ZENODO_SHA256SUMS"
MACHINE_PROOF = PUBLICATION / "MACHINE_PROOF_BUNDLE.json"
ZENODO_CANDIDATE = RELEASE / "ZENODO_DEPOSITION_CANDIDATE.json"
AUTHORIZATION_REQUIRED = RELEASE / "EXTERNAL_EFFECT_AUTHORIZATION_REQUIRED.md"

EXACT_HEAD = "c5135ec43ea81945cb9840c9a0eb795fb6dcde96"
EXACT_BASE = "8441daccfea2cd132048a08ee16e40595db0cf7e"
EXACT_BRANCH = "candidate/scientific-fact-growth-mesh-v1"
RETURNED_AT = "2026-08-01T20:45:53+02:00"

POLICY = {
    "id": "qikvrt-zenodo-machine-proof-before-publication-v2",
    "path": "policy/zenodo-machine-proof-policy-v2.json",
    "version": "2.0.0",
    "sha256": "933d6322a1e294848c6385d1384ab0ec3862c8675ebe35ec2fc4cad3e0baec47",
    "git_blob_sha1": "e9578d30d22f845e7df684128dcd9332641c00be",
}

THEOREM_AXIOMS = [
    ("QIKVRT.V2.Knowledge.formalProved_requires_proved", ["propext"]),
    ("QIKVRT.V2.Knowledge.openClass_requires_openStatus", ["propext"]),
    ("QIKVRT.V2.Knowledge.append_extends", ["propext"]),
    ("QIKVRT.V2.Knowledge.merge_commutative_by_membership", ["propext"]),
    ("QIKVRT.V2.Knowledge.merge_associative", ["propext"]),
    ("QIKVRT.V2.Knowledge.merge_idempotent_by_membership", ["propext"]),
    ("QIKVRT.V2.Knowledge.replicas_converge_after_same_updates", ["propext"]),
    ("QIKVRT.V2.Knowledge.evidenceClosed_mono", []),
    ("QIKVRT.V2.Knowledge.answerability_mono", []),
    ("QIKVRT.V2.Knowledge.empty_corpus_answers_no_query", ["propext"]),
    (
        "QIKVRT.V2.Knowledge.corpus_relative_novelty_is_not_global",
        ["propext", "Quot.sound"],
    ),
    ("QIKVRT.V2.Knowledge.conflicts_are_preserved_by_extension", []),
    ("QIKVRT.V2.Knowledge.qualifiedObservation_eq_true_iff", ["propext"]),
    (
        "QIKVRT.V2.Knowledge.causallyAttributable_requires_identification",
        ["propext"],
    ),
    (
        "QIKVRT.V2.Knowledge.identical_trace_does_not_determine_physical_causation",
        [],
    ),
    (
        "QIKVRT.V2.Knowledge.twinActuation_requires_qualifiedObservation",
        ["propext"],
    ),
    ("QIKVRT.V2.Knowledge.twinActuation_requires_effectAck", ["propext"]),
    ("QIKVRT.V2.Knowledge.flatten_singletonSegments", ["propext"]),
    ("QIKVRT.V2.Knowledge.append_preserves_prefix", []),
    ("QIKVRT.V2.Knowledge.prefix_trans", ["propext"]),
    ("QIKVRT.V2.Knowledge.proposalOnly_never_authorizes_effect", []),
]

CANDIDATE_PATHS = [
    PUBLICATION / "QIK-VRT_Wissenschaftlicher_Faktenbau_2026-08-01.pdf",
    PUBLICATION / "QIK-VRT_Wissenschaftlicher_Faktenbau_2026-08-01.tex",
    PUBLICATION / "QIK-VRT_Kausalitaetsspiegel_Fachartikel_2026-08-01.pdf",
    PUBLICATION / "QIK-VRT_Kausalitaetsspiegel_Fachartikel_2026-08-01.tex",
    PUBLICATION / "FACHARTIKEL_DE.md",
    *[PUBLICATION / f"ARTICLE_WHATSAPP_{language}.md" for language in (
        "DE", "EN", "FR", "IT", "ES", "PT", "EL", "PL", "DA", "NB", "SV"
    )],
    IETF_STEM.with_suffix(".xml"),
    IETF_STEM.with_suffix(".txt"),
    IETF_STEM.with_suffix(".html"),
]

ARTIFACT_KINDS = {
    PUBLICATION / "README.md": "OTHER",
    PUBLICATION / "CITATION.cff": "OTHER",
    PUBLICATION / "LICENSE_NOTICE.md": "OTHER",
    PUBLICATION / "REFERENCES.bib": "SOURCE",
    CLAIM_MATRIX: "CLAIM_MATRIX",
    PUBLICATION / "SCIENTIFIC_FACT_GROWTH_PROTOCOL.md": "EVIDENCE",
    PUBLICATION / "EVIDENCE_BOUNDARY.md": "BOUNDARY_TEST",
    PUBLICATION / "PROTOCOL_IMPACT.md": "EVIDENCE",
    PUBLICATION / "EU_AI_ACT_AUDIT_READINESS.md": "EVIDENCE",
    PUBLICATION / "TRANSCRIPT_REVIEWED_DE.md": "SOURCE",
    PUBLICATION / "SOURCE_MEDIA_RECEIPT.json": "SOURCE",
    PUBLICATION / "FORMAL_ScientificFactGrowth.lean": "SOURCE",
    KERNEL_RECEIPT: "KERNEL_RECEIPT",
    PUBLICATION / "PDF_RENDER_VALIDATION.json": "EVIDENCE",
    PUBLICATION / "IETF_RENDER_VALIDATION.json": "EVIDENCE",
    IETF_STEM.with_suffix(".CANDIDATE.json"): "EVIDENCE",
    RETURN_RECEIPT: "RETURN_RECEIPT",
    FILESET: "OTHER",
    CHECKSUMS: "EVIDENCE",
}

WORDING = {
    "FORMAL_PROVED": ("PROVED", "ESTABLISHED_WITHIN_SCOPE"),
    "EMPIRICALLY_EVIDENCED": ("EVIDENCED", "EMPIRICALLY_SUPPORTED"),
    "SOURCE_BOUND": ("BOUND", "SOURCE_ATTRIBUTED"),
    "NORMATIVE": ("DECLARED", "NORMATIVE_DECLARATION"),
    "INTERPRETATIVE": ("DECLARED", "INTERPRETATIVE_DECLARATION"),
    "OPEN": ("OPEN", "EXPLICITLY_OPEN"),
}


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(  # noqa: S324 - canonical Git object identity
        f"blob {len(data)}\0".encode("ascii") + data
    ).hexdigest()


def data_for(path: pathlib.PurePosixPath, generated: Mapping[str, bytes]) -> bytes:
    key = path.as_posix()
    if key in generated:
        return generated[key]
    return (ROOT / key).read_bytes()


def identity(path: pathlib.PurePosixPath, generated: Mapping[str, bytes]) -> dict[str, Any]:
    data = data_for(path, generated)
    return {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob_sha1": git_blob_sha1(data),
    }


def kernel_receipt() -> dict[str, Any]:
    return {
        "_license": {
            "classification": "machine_readable_kernel_receipt",
            "copyright": "Copyright 2026 Ingolf Lohmann",
            "license": "Apache-2.0",
            "license_text_ref": "LICENSES/Apache-2.0.txt",
            "rights_holder": "Ingolf Lohmann",
        },
        "schema": "qikvrt_scientific_fact_growth_lean_kernel_receipt_v2",
        "generated_at": "2026-08-01T18:45:53Z",
        "repository": "Goldkelch/qik-vrt",
        "publication_id": PUBLICATION_ID,
        "scope_id": PUBLICATION_ID,
        "state": "KERNEL_VERIFIED",
        "scientific_receipt_stage": "H2_SUCCESSOR_MATERIALIZATION",
        "scientific_verification_stage": "H1_TARGET_EXACT_HEAD",
        "base_commit": EXACT_BASE,
        "candidate_state": "EXACT_HEAD_WORKFLOW_VERIFIED_PREDECESSOR_RECEIPT",
        "workflow": {
            "conclusion": "success",
            "event": "pull_request",
            "exact_head_bound": True,
            "ref": f"refs/heads/{EXACT_BRANCH}",
            "repository": "Goldkelch/qik-vrt",
            "run_attempt": "1",
            "run_id": "30712975179",
            "run_number": 2798,
            "sha": EXACT_HEAD,
            "workflow_name": "QIKVRT CI",
        },
        "supporting_workflows": [
            {"name": "QIK-VRT manuscript proof coverage", "run_id": "30712975193", "run_number": 324, "conclusion": "success"},
            {"name": "QIKVRT repository evidence materialization", "run_id": "30712975184", "run_number": 756, "conclusion": "success", "fixpoint": "Repository evidence is already current."},
            {"name": "QIK-VRT global claim completion", "run_id": "30712975214", "run_number": 343, "conclusion": "success"},
            {"name": "QIKVRT Collective Proposal Review", "run_id": "30712975186", "run_number": 870, "conclusion": "success"},
            {"name": "QIKVRT live status watch", "run_id": "30712975187", "run_number": 1127, "conclusion": "success"},
        ],
        "compiler": {
            "name": "Lean",
            "version": "4.19.0",
            "target": "x86_64-unknown-linux-gnu",
            "commit": "6caaee842e94",
            "build": "Release",
            "lake_version": "5.0.0-6caaee8",
            "official_archive_url": "https://github.com/leanprover/lean4/releases/download/v4.19.0/lean-4.19.0-linux.tar.zst",
            "official_archive_sha256_observed": "6fe3ce97a58f44e2b3567d455b994eacec5bfe9ae7774f2a573444480ba813fe",
        },
        "sandbox_compatibility": {
            "required": True,
            "reason": "Lean 4.19.0 resolves /proc/<own-pid>/exe while this sandbox exposes only the equivalent /proc/self/exe spelling.",
            "scope": "The preload shim rewrites only numeric /proc/.../exe readlink requests to /proc/self/exe and grants no additional filesystem or process access.",
            "shim_source_sha256": "283e1d6dec5e24339ec6bc356773a8d99318f0e65fd111fb2e2b6711577ec569",
            "shim_binary_sha256": "c61150cb3d9eb5efb822bef1f3d48f79dbb86630b1a2efd12c1c8902a5016d0f",
        },
        "formal_source": {
            "repository_path": "formalization/QIKVRT_Formalization_v2.0/QIKVRTFormalization/Knowledge/ScientificFactGrowth.lean",
            "publication_snapshot_path": str(PUBLICATION / "FORMAL_ScientificFactGrowth.lean"),
            "sha256": "e7538876d7c70b5c54885855a852e72f83ae0f9b49a2adb02d0ccb3f075b7307",
            "byte_identical_snapshot": True,
        },
        "command": "LD_PRELOAD=<attested-shim> PATH=<lean-4.19.0>/bin:$PATH lake build QIKVRTFormalization.Knowledge.ScientificFactGrowth",
        "exit_code": 0,
        "kernel_status": "VERIFIED",
        "theorem_count": len(THEOREM_AXIOMS),
        "sorry_ax_observed": False,
        "project_specific_axiom_observed": False,
        "allowed_foundational_axioms": ["propext", "Quot.sound"],
        "theorems": [theorem for theorem, _axioms in THEOREM_AXIOMS],
        "theorem_axioms": [
            {"theorem": theorem, "axioms": axioms}
            for theorem, axioms in THEOREM_AXIOMS
        ],
        "epistemic_boundary": {
            "proved": "Only the explicitly encoded finite corpus, merge, classification, observation, causality-record, digital-twin, message and proposal-only model properties.",
            "not_proved": [
                "truth of arbitrary natural-language statements",
                "global scientific novelty",
                "automatic proof synthesis completeness",
                "physical causation from a trace",
                "physical retrocausality",
                "quantum-to-classical emergence",
                "empirical cognitive improvement",
                "answers to every possible question",
            ],
        },
        "completion_claims": {
            "repository_promotion_complete": False,
            "zenodo_published": False,
            "ietf_submitted": False,
            "system_wide_completion": "UNCLAIMED",
            "effect_ack": "EFFECT_ACK_CONTINUE",
        },
    }


def fileset_text() -> str:
    names = [path.name for path in CANDIDATE_PATHS]
    names.extend(path.name for path in ARTIFACT_KINDS)
    names.append(MACHINE_PROOF.name)
    lines = "\n".join(f"- `{name}`" for name in names)
    return f"""<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Proposed Zenodo fileset

State: `FROZEN_CANDIDATE_AWAITING_EXACT_OWNER_AUTHORIZATION`

This file does not authorize an upload. The machine-proof bundle establishes
mechanical eligibility for exactly the listed bytes. A later repository-side
natural-person authorization must bind the exact return, metadata and
machine-proof SHA-256 values before any production Zenodo mutation.

## Exact upload files

{lines}

The raw M4A source is intentionally excluded. Its SHA-256 identity and local
transcription provenance are bound by `SOURCE_MEDIA_RECEIPT.json`. The IETF
files are an archival candidate only; inclusion here neither submits the draft
nor claims IETF consensus. `PASS`, `FINAL_PASS` and `EFFECT_ACK_DONE` remain
unclaimed.
"""


def metadata() -> dict[str, Any]:
    return {
        "access_right": "open",
        "creators": [
            {
                "affiliation": "Independent Researcher; QIK-VRT",
                "name": "Lohmann, Ingolf",
            }
        ],
        "description": (
            "<p>Diese Veröffentlichung operationalisiert QIK-VRT-Repositories als "
            "prüfbare Kausalitätsspiegel: Beobachtungen, Transformationen, Hypothesen, "
            "Entscheidungen, beabsichtigte Wirkungen und beobachtete Wirkungen werden "
            "provenienz- und statusgebunden erhalten, ohne Chronologie mit physikalischer "
            "Kausalität gleichzusetzen.</p><p>Der maschinengeprüfte Lean-4-Kern enthält "
            "21 Sätze über epistemische Typisierung, append-only Wachstum, Merge-Algebra, "
            "bedingte Replikakonvergenz, Konflikterhalt, corpus-relative Neuheit, "
            "Kausalitäts- und Digital-Twin-Gates, endliche Nachrichtenrekonstruktion und "
            "proposal-only Nichtwirkung. Der Korpus umfasst eine wissenschaftliche "
            "Monographie, einen allgemeinverständlichen Fachartikel, vorleseoptimierte "
            "Fassungen in elf europäischen Sprachen, Quellen- und Render-Receipts sowie "
            "einen nicht eingereichten IETF-Internet-Draft-Kandidaten.</p><p>Nicht bewiesen "
            "werden universelle Wahrheit, globale wissenschaftliche Neuheit, vollständige "
            "Natural-Language-to-Lean-Automation, Antworten auf jede Frage, physische "
            "Retrokausalität, ein Quanten-zu-Klassik-Beweis oder allgemeine empirische "
            "Kognitionsverbesserung.</p>"
        ),
        "keywords": [
            "QIK-VRT",
            "causality mirror",
            "scientific claim assurance",
            "formal verification",
            "Lean 4",
            "append-only evidence",
            "provenance",
            "digital twin",
            "measurement and control",
            "quantum-classical interface",
            "machine-verifiable science",
            "AI auditability",
        ],
        "language": "deu",
        "license": "cc-by-nc-nd-4.0",
        "notes": (
            "Zenodo-Persistenz würde Identität, Version und Verfügbarkeit der "
            "veröffentlichten Bytes belegen, nicht Peer Review oder die Wahrheit der "
            "ausdrücklich offenen physikalischen und empirischen Hypothesen. Software- "
            "und Lean-Dateien behalten ihre jeweiligen dateibezogenen Lizenzen. "
            "PASS, FINAL_PASS und EFFECT_ACK_DONE werden nicht beansprucht."
        ),
        "prereserve_doi": True,
        "publication_date": "2026-08-01",
        "publication_type": "workingpaper",
        "related_identifiers": [
            {
                "identifier": "https://github.com/Goldkelch/qik-vrt",
                "relation": "isSupplementTo",
                "scheme": "url",
            }
        ],
        "title": "QIK-VRT als Kausalitätsspiegel: Ein maschinenverifizierbares Protokoll für wissenschaftliches Faktenwachstum",
        "upload_type": "publication",
        "version": "1.0.0",
    }


def materialize() -> dict[str, bytes]:
    generated: dict[str, bytes] = {}

    generated[KERNEL_RECEIPT.as_posix()] = json_bytes(kernel_receipt())

    matrix = json.loads((ROOT / CLAIM_MATRIX).read_text(encoding="utf-8"))
    matrix["receipt_sha256"] = hashlib.sha256(
        generated[KERNEL_RECEIPT.as_posix()]
    ).hexdigest()
    generated[CLAIM_MATRIX.as_posix()] = json_bytes(matrix)
    generated[FILESET.as_posix()] = fileset_text().encode("utf-8")

    candidate_files: list[dict[str, Any]] = []
    for path in CANDIDATE_PATHS:
        candidate_files.append(
            {
                **identity(path, generated),
                "name": path.name,
                "path": path.as_posix(),
                "role": "PRIMARY"
                if path == CANDIDATE_PATHS[0]
                else "SUPPLEMENT",
            }
        )

    return_value = {
        "_license": {
            "classification": "machine_readable_prepublication_return_receipt",
            "copyright": "Copyright 2026 Ingolf Lohmann",
            "license": "CC-BY-NC-ND-4.0",
            "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
            "rights_holder": "Ingolf Lohmann",
        },
        "schema": "qikvrt_prepublication_return_receipt_v2",
        "publication_id": PUBLICATION_ID,
        "content_changed": False,
        "original_files": [],
        "candidate_files": [
            {key: item[key] for key in ("path", "bytes", "sha256", "git_blob_sha1")}
            for item in candidate_files
        ],
        "changed_claim_ids": [],
        "change_reasons": [],
        "change_notice_path": None,
        "return": {
            "candidate_returned_to_owner": True,
            "owner_name": "Ingolf Lohmann",
            "owner_type": "NATURAL_PERSON",
            "return_channel": "ChatGPT conversation with repository and Library byte links",
            "returned_at": RETURNED_AT,
            "visible_change_notice_returned": False,
        },
    }
    generated[RETURN_RECEIPT.as_posix()] = json_bytes(return_value)

    checksum_paths = sorted(
        [*CANDIDATE_PATHS, *[path for path in ARTIFACT_KINDS if path != CHECKSUMS]],
        key=lambda item: item.name,
    )
    generated[CHECKSUMS.as_posix()] = "".join(
        f"{identity(path, generated)['sha256']}  {path.name}\n"
        for path in checksum_paths
    ).encode("utf-8")

    artifact_files = [
        {
            "path": path.as_posix(),
            "sha256": identity(path, generated)["sha256"],
            "git_blob_sha1": identity(path, generated)["git_blob_sha1"],
            "kind": kind,
        }
        for path, kind in ARTIFACT_KINDS.items()
    ]

    claims: list[dict[str, Any]] = []
    receipt_ref = KERNEL_RECEIPT.as_posix()
    source_ref = (PUBLICATION / "SOURCE_MEDIA_RECEIPT.json").as_posix()
    for item in matrix["claims"]:
        status, publication_wording = WORDING[item["classification"]]
        proof_refs = [f"{receipt_ref}#{theorem}" for theorem in item["proof_refs"]]
        source_refs = (
            [f"{source_ref}#audio_source"]
            if item["claim_id"] == "SFG-024"
            else []
        )
        claims.append(
            {
                "claim_id": item["claim_id"],
                "statement": item["statement"],
                "classification": item["classification"],
                "status": status,
                "publication_wording": publication_wording,
                "scope": item["boundary"],
                "proof_refs": proof_refs,
                "evidence_refs": [],
                "source_refs": source_refs,
            }
        )

    bundle = {
        "_license": {
            "classification": "machine_readable_proof_bundle",
            "copyright": "Copyright 2026 Ingolf Lohmann",
            "license": "CC-BY-NC-ND-4.0",
            "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
            "rights_holder": "Ingolf Lohmann",
        },
        "schema": "qikvrt_zenodo_machine_proof_bundle_v2",
        "policy": POLICY,
        "publication_id": PUBLICATION_ID,
        "candidate": {
            "files": candidate_files,
            "primary_document_path": CANDIDATE_PATHS[0].as_posix(),
        },
        "claims": claims,
        "artifacts": artifact_files,
        "prepublication_return": {
            "candidate_returned_to_owner": True,
            "change_notice_path": None,
            "content_changed": False,
            "receipt_path": RETURN_RECEIPT.as_posix(),
        },
        "gates": {
            "all_claims_dispositioned": True,
            "all_references_resolve": True,
            "candidate_frozen": True,
            "formal_claims_have_kernel_receipts": True,
            "open_claims_not_worded_as_facts": True,
            "proof_bundle_in_upload_fileset": True,
            "returned_bytes_equal_upload_bytes": True,
        },
        "completion_claims": {
            "machine_proof_complete": True,
            "zenodo_upload_authorized": True,
        },
    }
    generated[MACHINE_PROOF.as_posix()] = json_bytes(bundle)

    metadata_value = metadata()
    metadata_sha256 = hashlib.sha256(canonical_json_bytes(metadata_value)).hexdigest()
    proof_identity = identity(MACHINE_PROOF, generated)
    return_identity = identity(RETURN_RECEIPT, generated)
    authorization_id = f"qikvrt-sfg-mesh-zenodo-v1-{proof_identity['sha256'][:8]}"
    zenodo_statement = (
        "AUTHORIZE_EXACT_UPLOAD "
        f"authorization_id={authorization_id} "
        f"publication_id={PUBLICATION_ID} "
        f"return_sha256={return_identity['sha256']} "
        f"metadata_sha256={metadata_sha256} "
        f"machine_proof_sha256={proof_identity['sha256']}"
    )
    ietf_candidate = json.loads(
        (ROOT / IETF_STEM.with_suffix(".CANDIDATE.json")).read_text(encoding="utf-8")
    )
    ietf_statement = (
        "AUTHORIZE_EXACT_IETF_SUBMISSION "
        "draft_name=draft-lohmann-qikvrt-scientific-claim-assurance-00 "
        f"xml_sha256={ietf_candidate['artifacts']['xml']['sha256']} "
        f"txt_sha256={ietf_candidate['artifacts']['txt']['sha256']} "
        f"html_sha256={ietf_candidate['artifacts']['html']['sha256']}"
    )
    upload_paths = [
        *(item["path"] for item in candidate_files),
        *(item["path"] for item in artifact_files),
        MACHINE_PROOF.as_posix(),
    ]
    release_candidate = {
        "_license": {
            "classification": "repository_side_external_effect_candidate",
            "copyright": "Copyright 2026 Ingolf Lohmann",
            "license": "CC-BY-NC-ND-4.0",
            "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
            "rights_holder": "Ingolf Lohmann",
        },
        "schema": "qikvrt_scientific_fact_growth_external_effect_candidate_v1",
        "state": "AWAITING_EXACT_OWNER_AUTHORIZATION",
        "repository": "Goldkelch/qik-vrt",
        "publication_id": PUBLICATION_ID,
        "verified_predecessor_head": EXACT_HEAD,
        "source_head_binding": "BIND_SUCCESSOR_HEAD_IN_REPOSITORY_SIDE_OWNER_AUTHORIZATION",
        "metadata": metadata_value,
        "canonical_metadata_sha256": metadata_sha256,
        "candidate_return_receipt": {
            "path": RETURN_RECEIPT.as_posix(),
            **return_identity,
        },
        "machine_proof": {
            "path": MACHINE_PROOF.as_posix(),
            **proof_identity,
        },
        "upload_paths": upload_paths,
        "authorization_id": authorization_id,
        "exact_zenodo_authorization_statement": zenodo_statement,
        "exact_ietf_authorization_statement": ietf_statement,
        "external_effects": {
            "zenodo_production_upload_performed": False,
            "ietf_datatracker_submission_performed": False,
            "owner_authorization_consumed": False,
        },
        "completion_claims": {
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
            "system_wide_completion": "UNCLAIMED",
        },
    }
    generated[ZENODO_CANDIDATE.as_posix()] = json_bytes(release_candidate)
    generated[AUTHORIZATION_REQUIRED.as_posix()] = f"""<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Exact external-effect authorizations required

No website form entry is requested. To authorize the frozen candidates, return
the applicable line verbatim in the ChatGPT conversation. These lines do not
record an effect; they only authorize the separately gated attempt.

## Zenodo production upload

```text
{zenodo_statement}
```

## IETF Datatracker submission

```text
{ietf_statement}
```

Current state: neither external effect has been performed. `PASS`,
`FINAL_PASS` and `EFFECT_ACK_DONE` remain unclaimed.
""".encode("utf-8")
    return generated


def apply_outputs(outputs: Mapping[str, bytes], check: bool) -> int:
    drift: list[str] = []
    for relative, expected in outputs.items():
        path = ROOT / relative
        observed = path.read_bytes() if path.is_file() else None
        if observed == expected:
            continue
        if check:
            drift.append(relative)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(expected)
    if drift:
        for relative in drift:
            print(f"DRIFT {relative}", file=sys.stderr)
        return 2
    print(
        "SCIENTIFIC_FACT_GROWTH_RELEASE_STATE="
        + ("current" if check else "materialized")
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Materialize or check the scientific fact-growth release envelope"
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    return apply_outputs(materialize(), args.check)


if __name__ == "__main__":
    raise SystemExit(main())
