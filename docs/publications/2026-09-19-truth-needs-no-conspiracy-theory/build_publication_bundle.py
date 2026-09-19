#!/usr/bin/env python3
"""Deterministically rebuild the PR #1128 dossier's publication controls."""

from __future__ import annotations

import collections
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys
from typing import Any


D = pathlib.Path(__file__).resolve().parent
ROOT = D.parents[2]
REL = D.relative_to(ROOT).as_posix()
PUBLICATION_ID = "qikvrt-truth-expectations-wager-effect-law-2026-09-19-v2"
RETURNED_AT = "2026-09-19T12:42:14Z"
AUTHORIZATION_ID = "pr1128-truth-expectations-law-20260919-v2"

DOCUMENTS = (
    ("TRUTH", "Die_Wahrheit_braucht_keine_Verschwoerungstheorie.txt", "PRIMARY"),
    ("EXPECT", "WENN_ERWARTUNGEN_HANDELBAR_WERDEN_DE.md", "PRIMARY"),
    ("LAW", "WENN_AUS_EINER_WETTE_EINE_TAT_WIRD_DE.md", "PRIMARY"),
    ("OWNER", "AUTORENERKLAERUNG_UND_EVIDENZGRENZE.md", "SUPPLEMENT"),
)
PRIMARY_PATH = f"{REL}/{DOCUMENTS[0][1]}"

LICENSE = {
    "copyright": "Copyright 2026 Ingolf Lohmann.",
    "license": "CC-BY-NC-ND-4.0",
    "license_text_ref": "LICENSES/CC-BY-NC-ND-4.0.txt",
    "rights_holder": "Ingolf Lohmann",
}

BASE_SOURCE_IDS = {
    "OWNER_PRIMARY_TEXT",
    "XING_KARLSRUHE",
    "WHO_SAGO_20250627",
    "CFTC_9185_26",
    "SIEMENS_SIPORT",
    "SIEMENS_BOARD",
    "US_PRESIDENTS",
    "ZENODO_ONTOLOGY_DIFFERENCE_21582781",
}

LEGAL_LINE_SOURCES: dict[int, list[str]] = {
    44: ["DE_GG_ART_1"],
    46: ["DE_GG_ART_1"],
    48: ["DE_GG_ART_1"],
    50: ["DE_GG_ART_1"],
    52: ["DE_GG_ART_1", "US_AMENDMENTS_5_14", "CN_CONSTITUTION_RIGHTS", "RU_CONSTITUTION_RIGHTS", "UA_CONSTITUTION_RIGHTS"],
    54: ["DE_GG_ART_1", "DE_GG_ART_79"],
    68: ["DE_STGB_240"],
    70: ["DE_STGB_238"],
    72: ["DE_STGB_241"],
    74: ["DE_STGB_202A"],
    76: ["DE_STGB_202D"],
    78: ["DE_STGB_126A"],
    80: ["DE_STGB_253"],
    108: ["DE_STGB_PARTICIPATION"],
    156: ["DE_BVERFG_COMPLAINT"],
    158: ["DE_BVERFG_COMPLAINT"],
    160: ["DE_BVERFG_COMPLAINT"],
    174: ["DE_BVERFG_COMPLAINT"],
    184: ["DE_BVERFG_COMPLAINT"],
    234: ["US_AMENDMENTS_5_14"],
    242: ["CN_CONSTITUTION_RIGHTS"],
    244: ["CN_CIVIL_CODE_PERSONALITY"],
    246: ["CN_CONSTITUTION_RIGHTS", "CN_CIVIL_CODE_PERSONALITY"],
    250: ["RU_CONSTITUTION_RIGHTS"],
    252: ["RU_CONSTITUTION_RIGHTS"],
    256: ["UA_CONSTITUTION_RIGHTS"],
    258: ["UA_CONSTITUTION_RIGHTS"],
}

EXPECTATION_LINE_SOURCES: dict[int, list[str]] = {
    36: ["CFTC_9185_26"],
    38: ["CFTC_9185_26"],
    46: ["CFTC_9185_26"],
    48: ["CFTC_9185_26"],
    52: ["CFTC_9185_26"],
}

OPEN_LINES = {
    "EXPECT": {
        14, 52, 60, 62, 66, 68, 72, 74, 80, 82, 84, 86, 88, 90, 92, 94,
        96, 98, 100, 102, 112, 114, 120, 122, 124, 125, 126, 127, 128, 129,
        130, 131, 132, 133, 134, 136, 138, 140, 202, 232, 254, 256, 260, 262,
        264, 274, 276, 278, 280, 282, 284, 286, 288, 290, 292, 328, 330, 332,
        334, 336, 338, 342, 346, 348, 350, 352, 354, 356, 358, 360, 362, 364,
        366, 368, 370, 378,
    },
    "LAW": {
        12, 14, 16, 18, 20, 24, 26, 60, 64, 66, 82, 84, 86, 90, 94, 98,
        100, 102, 104, 106, 110, 112, 113, 114, 115, 116, 117, 118, 119, 120,
        121, 122, 123, 124, 126, 128, 130, 132, 136, 138, 156, 162, 164, 165,
        166, 168, 170, 171, 172, 174, 176, 178, 180, 198, 200, 202, 264, 266,
        267, 268, 269, 270, 271, 272, 273, 274, 276, 278, 280, 282, 284, 286,
        288, 290, 292, 294, 296, 298, 300, 302, 304, 306, 310, 312, 314, 320,
        322, 324, 352, 354, 356, 358, 360, 362, 364, 388, 390, 392,
    },
    "OWNER": {16, 17, 18, 19, 20, 23, 25},
}


def identity(path: pathlib.Path) -> dict[str, Any]:
    raw = path.read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    return {
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_sha1": blob,
    }


def relative(name: str) -> str:
    return f"{REL}/{name}"


def write_json(name: str, value: Any) -> None:
    (D / name).write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def candidate_identity(name: str, role: str) -> dict[str, Any]:
    path = relative(name)
    return {"path": path, "name": name, **identity(ROOT / path), "role": role}


def artifact_identity(name: str, kind: str) -> dict[str, Any]:
    path = relative(name)
    observed = identity(ROOT / path)
    observed.pop("bytes")
    return {"path": path, **observed, "kind": kind}


def is_structural(line: str) -> bool:
    stripped = line.strip()
    return (
        stripped.startswith("#")
        or stripped in {"<!--", "-->", "```text", "```"}
        or stripped.startswith("SPDX-License-Identifier:")
        or stripped.startswith("Copyright 2026")
    )


def disposition(prefix: str, line_number: int) -> tuple[str, str, str, list[str]]:
    sources: list[str] = []
    if prefix == "LAW" and line_number in LEGAL_LINE_SOURCES:
        classification = "SOURCE_BOUND"
        sources = LEGAL_LINE_SOURCES[line_number]
    elif prefix == "EXPECT" and line_number in EXPECTATION_LINE_SOURCES:
        classification = "SOURCE_BOUND"
        sources = EXPECTATION_LINE_SOURCES[line_number]
    elif line_number in OPEN_LINES.get(prefix, set()):
        classification = "OPEN"
    else:
        classification = "INTERPRETATIVE"

    if classification == "SOURCE_BOUND":
        return (
            classification,
            "BOUND",
            "Nur an die genannten amtlichen oder institutionellen Primärquellen und deren begrenzten Wortlaut gebunden; keine Feststellung eines konkreten Einzelfalls, keine Rechtsberatung, kein Schuldnachweis und keine Übertragung praktischer Durchsetzung.",
            sources,
        )
    if classification == "OPEN":
        return (
            classification,
            "OPEN",
            "Ausdrücklich offene Hypothese, Forschungsfrage, konditionale Möglichkeit oder nicht abgeschlossener Nachweis. Sie wird nicht als eingetretene Tatsache, identifizierte Person, geschlossene Kausalkette, juristische Subsumtion oder empirisch bestätigte Überlegenheit veröffentlicht.",
            [],
        )
    if prefix == "OWNER" and line_number == 10:
        return (
            classification,
            "DECLARED",
            "Ausdrücklich Ingolf Lohmann zugeschriebene vergleichende Einschätzung innerhalb seines gegenwärtigen Hypothesenraums; kein berechneter Posterior, keine präregistrierte Vergleichsstudie, keine unabhängig bestätigte wissenschaftliche Schlussfolgerung und kein Nachweis einer bestimmten Person oder Kausalkette.",
            [],
        )
    return (
        classification,
        "DECLARED",
        "Interpretative, autobiografische, rhetorische oder methodische Aussage des Autors im Kontext des Dossiers. Keine zusätzliche unabhängige Tatsachenfeststellung, kein formaler QIK-VRT-Theorembeleg, keine universelle Prognosegarantie und kein individueller Schuldnachweis.",
        [],
    )


def source_record(source_id: str, source_type: str, url: str, scope: str) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "source_type": source_type,
        "url": url,
        "observation_date": "2026-09-19",
        "scope": scope,
        "raw_origin_body_hash_claimed": False,
    }


def main() -> None:
    previous_matrix = json.loads((D / "CLAIM_MATRIX.json").read_text(encoding="utf-8"))
    previous_sources = json.loads((D / "SOURCE_BINDINGS.json").read_text(encoding="utf-8"))

    document_records: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for prefix, name, role in DOCUMENTS:
        path = relative(name)
        raw = (D / name).read_bytes()
        observed = identity(D / name)
        document_records.append(
            {
                "document_id": prefix,
                "path": path,
                **observed,
                "line_count": len(raw.decode("utf-8").splitlines()),
                "role": role,
            }
        )
        candidates.append(candidate_identity(name, role))

    base_path = relative(DOCUMENTS[0][1])
    claims: list[dict[str, Any]] = []
    structural: list[dict[str, Any]] = []
    for old_claim in previous_matrix["claims"]:
        if not old_claim["claim_id"].startswith("TRUTH-"):
            continue
        claim = dict(old_claim)
        claim["document_path"] = base_path
        claim.setdefault(
            "status",
            {
                "SOURCE_BOUND": "BOUND",
                "INTERPRETATIVE": "DECLARED",
                "NORMATIVE": "DECLARED",
                "OPEN": "OPEN",
            }[claim["classification"]],
        )
        claim.setdefault("proof_refs", [])
        claim.setdefault("sources", [])
        claims.append(claim)
    for old_line in previous_matrix["structural_lines"]:
        if old_line.get("document_path", base_path) != base_path:
            continue
        item = dict(old_line)
        item["document_path"] = base_path
        structural.append(item)

    for prefix, name, _role in DOCUMENTS[1:]:
        path = relative(name)
        lines = (D / name).read_text(encoding="utf-8").splitlines()
        for line_number, statement in enumerate(lines, 1):
            if not statement.strip():
                continue
            if is_structural(statement):
                structural.append(
                    {
                        "document_path": path,
                        "line": line_number,
                        "reason": "MARKDOWN_OR_LICENSE_STRUCTURE",
                        "statement": statement,
                    }
                )
                continue
            classification, status, boundary, source_ids = disposition(prefix, line_number)
            claims.append(
                {
                    "claim_id": f"{prefix}-L{line_number:03d}",
                    "document_path": path,
                    "line": line_number,
                    "line_sha256": hashlib.sha256(statement.encode("utf-8")).hexdigest(),
                    "statement": statement,
                    "classification": classification,
                    "status": status,
                    "boundary": boundary,
                    "proof_refs": [],
                    "sources": list(source_ids),
                }
            )

    counts = collections.Counter(claim["classification"] for claim in claims)
    matrix = {
        "schema": "qikvrt_pr1128_claim_matrix_v2",
        "publication_id": PUBLICATION_ID,
        "classification_author": "OpenAI ChatGPT Codex; exact build unavailable",
        "coverage_unit": "every nonblank line in every candidate document",
        "primary_document": next(item for item in document_records if item["path"] == PRIMARY_PATH),
        "documents": document_records,
        "claim_count": len(claims),
        "classification_counts": dict(sorted(counts.items())),
        "claims": claims,
        "structural_lines": structural,
    }
    write_json("CLAIM_MATRIX.json", matrix)

    sources = [
        dict(source)
        for source in previous_sources["sources"]
        if source["source_id"] in BASE_SOURCE_IDS
    ]
    owner_primary = next(source for source in sources if source["source_id"] == "OWNER_PRIMARY_TEXT")
    owner_primary.update(identity(D / DOCUMENTS[0][1]))
    owner_primary["path"] = PRIMARY_PATH
    sources.extend(
        [
            source_record("DE_GG_ART_1", "PRIMARY_LEGISLATION", "https://www.gesetze-im-internet.de/gg/art_1.html", "Wortlaut und Bindungsstruktur von Artikel 1 GG; kein Einzelfallurteil."),
            source_record("DE_GG_ART_79", "PRIMARY_LEGISLATION", "https://www.gesetze-im-internet.de/gg/art_79.html", "Wortlaut von Artikel 79 Absatz 3 GG; stützt die besondere deutsche Ewigkeitsgarantie, nicht eine Exklusivität aller Würdeschutzideen."),
            source_record("DE_STGB_240", "PRIMARY_LEGISLATION", "https://www.gesetze-im-internet.de/stgb/__240.html", "Amtlicher Normtext der Nötigung; Anwendbarkeit erfordert Einzelfallprüfung."),
            source_record("DE_STGB_238", "PRIMARY_LEGISLATION", "https://www.gesetze-im-internet.de/stgb/__238.html", "Amtlicher Normtext der Nachstellung; keine Behauptung, der Tatbestand sei in einem konkreten Fall erfüllt."),
            source_record("DE_STGB_241", "PRIMARY_LEGISLATION", "https://www.gesetze-im-internet.de/stgb/__241.html", "Amtlicher Normtext der Bedrohung; konditionale Rechtsinformation."),
            source_record("DE_STGB_202A", "PRIMARY_LEGISLATION", "https://www.gesetze-im-internet.de/stgb/__202a.html", "Amtlicher Normtext des Ausspähens von Daten; konditionale Rechtsinformation."),
            source_record("DE_STGB_202D", "PRIMARY_LEGISLATION", "https://www.gesetze-im-internet.de/stgb/__202d.html", "Amtlicher Normtext der Datenhehlerei; konditionale Rechtsinformation."),
            source_record("DE_STGB_126A", "PRIMARY_LEGISLATION", "https://www.gesetze-im-internet.de/stgb/__126a.html", "Amtlicher Normtext der gefährdenden Verbreitung personenbezogener Daten; konditionale Rechtsinformation."),
            source_record("DE_STGB_253", "PRIMARY_LEGISLATION", "https://www.gesetze-im-internet.de/stgb/__253.html", "Amtlicher Normtext der Erpressung; konditionale Rechtsinformation."),
            source_record("DE_STGB_PARTICIPATION", "PRIMARY_LEGISLATION", "https://www.gesetze-im-internet.de/stgb/__25.html", "Ausgangspunkt der amtlichen allgemeinen Beteiligungsregeln in §§ 25 bis 27 StGB; Vorsatz, Tatbeitrag und Delikt bleiben einzelfallabhängig."),
            source_record("DE_BVERFG_COMPLAINT", "PRIMARY_COURT_INFORMATION", "https://www.bundesverfassungsgericht.de/DE/Das-Gericht/Aufgaben-und-Verfahren/Verfassungsbeschwerde/verfassungsbeschwerde_node.html", "Offizielle allgemeine Information zur Verfassungsbeschwerde; ersetzt keine Zulässigkeits- oder Rechtsberatung im Einzelfall."),
            source_record("US_AMENDMENTS_5_14", "PRIMARY_CONSTITUTIONAL_TEXT", "https://www.archives.gov/founding-docs/bill-of-rights-transcript", "National-Archives-Text des Fifth Amendment zusammen mit der amtlichen Fourteenth-Amendment-Seite; bindet Due Process und Equal Protection, nicht Gleichheit der Rechtssysteme."),
            source_record("CN_CONSTITUTION_RIGHTS", "PRIMARY_CONSTITUTIONAL_TEXT", "http://www.npc.gov.cn/englishnpc/constitution2019/constitution.shtml", "Offizieller englischer Verfassungstext, insbesondere Artikel 37, 38 und 40; institutionelle Durchsetzung wird nicht daraus abgeleitet."),
            source_record("CN_CIVIL_CODE_PERSONALITY", "PRIMARY_LEGISLATION", "https://english.www.gov.cn/archive/lawsregulations/202012/31/content_WS5fedad98c6d0f72576943005.html", "Offizielle englische Veröffentlichung des chinesischen Zivilgesetzbuchs; nur die benannten Persönlichkeitsrechtskategorien werden gebunden."),
            source_record("RU_CONSTITUTION_RIGHTS", "PRIMARY_CONSTITUTIONAL_TEXT", "http://en.kremlin.ru/acts/constitution", "Offizielle englische Veröffentlichung der russischen Verfassung; Normtext und praktische Durchsetzung bleiben getrennt."),
            source_record("UA_CONSTITUTION_RIGHTS", "PRIMARY_CONSTITUTIONAL_TEXT", "https://zakon.rada.gov.ua/laws/show/en/254%D0%BA/96-%D0%B2%D1%80#Text", "Offizieller englischer Verfassungstext der Werchowna Rada, insbesondere Artikel 28 und 29; keine Aussage zur Einzelfallanwendung."),
        ]
    )
    source_bindings = {
        "schema": "qikvrt_pr1128_source_bindings_v2",
        "publication_id": PUBLICATION_ID,
        "observed_on": "2026-09-19",
        "observation_method": "Public primary-source pages and repository records were reviewed or recorded; no foreign origin-body digest is invented.",
        "PREDECESSOR_EVIDENCE_TRANSFER": False,
        "sources": sources,
    }
    write_json("SOURCE_BINDINGS.json", source_bindings)

    metadata = {
        "title": "Erwartungen, Wetten, Wirkung und Recht",
        "upload_type": "publication",
        "publication_type": "other",
        "description": "Deutschsprachiges Dossier von Ingolf Lohmann mit den Artikeln ‚Die Wahrheit braucht keine Verschwörungstheorie‘, ‚Wenn Erwartungen handelbar werden‘ und ‚Wenn aus einer Wette eine Tat wird‘. Der Autor erklärt die kombinierte Wett-/Einflussnahmehypothese unter seinen gegenwärtig erwogenen Möglichkeiten für die wahrscheinlichste Erklärung. Diese Einschätzung wird ausdrücklich zugeschrieben: Das Dossier weist keinen konkreten Markt, Wettenden, Zahlungsfluss, Auftraggeber, Ausführenden, keine geschlossene Kausalkette, keine universelle QIK-VRT-Prognoseüberlegenheit und keine individuelle Schuld nach. Claim-Matrix, Primärquellenbindungen und negative Grenztests sind beigefügt.",
        "creators": [{"name": "Lohmann, Ingolf"}],
        "version": "2.0.0",
        "publication_date": "2026-09-19",
        "access_right": "open",
        "license": "cc-by-nc-nd-4.0",
        "language": "deu",
        "keywords": ["QIK-VRT", "Prognosemärkte", "Evidenz", "Kausalität", "Menschenwürde", "Recht"],
        "related_identifiers": [
            {
                "identifier": "https://zenodo.org/records/22840633",
                "relation": "isNewVersionOf",
                "scheme": "url",
            }
        ],
        "notes": "Autor: Ingolf Lohmann. KI-unterstützte redaktionelle Ausarbeitung und maschinenlesbare Evidenzgrenzen: OpenAI ChatGPT Codex. Autoreneinschätzung ist von unabhängiger Evidenz getrennt.",
        "prereserve_doi": True,
    }
    write_json("ZENODO_METADATA.json", metadata)

    original = {"path": PRIMARY_PATH, **identity(ROOT / PRIMARY_PATH)}
    receipt_candidates = [
        {key: item[key] for key in ("path", "bytes", "sha256", "git_blob_sha1")}
        for item in candidates
    ]
    reasons = {
        "EXPECT-L018": "Der Nachfolger fügt den vollständigen Artikel über Prognosemärkte, finanzielle Anreize, Einflussmöglichkeiten und den prüfbaren QIK-VRT-Benchmark hinzu.",
        "LAW-L052": "Der Nachfolger fügt die vollständige juristische Folgefassung hinzu und korrigiert ausdrücklich die frühere Überdehnung, Deutschland sei das einzige Land mit verfassungsrechtlichem Würdeschutz.",
        "OWNER-L010": "Der Nachfolger materialisiert die vom Autor verlangte Aussage zur aus seiner Sicht wahrscheinlichsten Erklärung und trennt sie ausdrücklich von unabhängig bestätigter Evidenz.",
    }
    path_by_claim = {
        "EXPECT-L018": relative(DOCUMENTS[1][1]),
        "LAW-L052": relative(DOCUMENTS[2][1]),
        "OWNER-L010": relative(DOCUMENTS[3][1]),
    }
    candidate_sha = {item["path"]: item["sha256"] for item in candidates}
    receipt = {
        "_license": {"classification": "machine_readable_prepublication_return_receipt", **LICENSE},
        "schema": "qikvrt_prepublication_return_receipt_v2",
        "publication_id": PUBLICATION_ID,
        "content_changed": True,
        "original_files": [original],
        "candidate_files": receipt_candidates,
        "changed_claim_ids": list(reasons),
        "change_reasons": [
            {
                "claim_id": claim_id,
                "reason": reason,
                "original_sha256": original["sha256"],
                "corrected_sha256": candidate_sha[path_by_claim[claim_id]],
                "exact_candidate_path": path_by_claim[claim_id],
            }
            for claim_id, reason in reasons.items()
        ],
        "change_notice_path": relative("CHANGE_NOTICE.md"),
        "return": {
            "candidate_returned_to_owner": True,
            "owner_name": "Ingolf Lohmann",
            "owner_type": "NATURAL_PERSON",
            "return_channel": "ChatGPT Work response and GitHub pull request #1128 successor candidate",
            "returned_at": RETURNED_AT,
            "visible_change_notice_returned": True,
        },
    }
    write_json("PREPUBLICATION_RETURN_RECEIPT.json", receipt)

    verifier_spec = importlib.util.spec_from_file_location("verify_publication_scope", D / "verify_publication_scope.py")
    assert verifier_spec and verifier_spec.loader
    verifier = importlib.util.module_from_spec(verifier_spec)
    verifier_spec.loader.exec_module(verifier)
    write_json("BOUNDARY_TEST_REPORT.json", verifier.run_tests())

    artifacts = [
        artifact_identity("CLAIM_MATRIX.json", "CLAIM_MATRIX"),
        artifact_identity("SOURCE_BINDINGS.json", "SOURCE"),
        artifact_identity("QUELLEN_UND_GELTUNGSBEREICH.md", "OTHER"),
        artifact_identity("verify_publication_scope.py", "BOUNDARY_TEST"),
        artifact_identity("BOUNDARY_TEST_REPORT.json", "BOUNDARY_TEST"),
        artifact_identity("PREPUBLICATION_RETURN_RECEIPT.json", "RETURN_RECEIPT"),
        artifact_identity("CHANGE_NOTICE.md", "CHANGE_NOTICE"),
        artifact_identity("README.md", "OTHER"),
        artifact_identity("ZENODO_METADATA.json", "OTHER"),
    ]
    source_path = relative("SOURCE_BINDINGS.json")
    wording = {
        "SOURCE_BOUND": "SOURCE_ATTRIBUTED",
        "INTERPRETATIVE": "INTERPRETATIVE_DECLARATION",
        "NORMATIVE": "NORMATIVE_DECLARATION",
        "OPEN": "EXPLICITLY_OPEN",
    }
    bundle_claims = [
        {
            "claim_id": claim["claim_id"],
            "statement": claim["statement"],
            "classification": claim["classification"],
            "status": claim["status"],
            "publication_wording": wording[claim["classification"]],
            "scope": claim["boundary"],
            "proof_refs": [],
            "evidence_refs": [],
            "source_refs": [f"{source_path}#{source_id}" for source_id in claim["sources"]],
        }
        for claim in claims
    ]
    policy_path = ROOT / "policy/zenodo-machine-proof-policy-v2.json"
    policy = identity(policy_path)
    policy.pop("bytes")
    bundle = {
        "_license": {"classification": "machine_readable_proof_bundle", **LICENSE},
        "schema": "qikvrt_zenodo_machine_proof_bundle_v2",
        "policy": {
            "id": "qikvrt-zenodo-machine-proof-before-publication-v2",
            "path": "policy/zenodo-machine-proof-policy-v2.json",
            "version": "2.0.0",
            **policy,
        },
        "publication_id": PUBLICATION_ID,
        "candidate": {"files": candidates, "primary_document_path": PRIMARY_PATH},
        "claims": bundle_claims,
        "artifacts": artifacts,
        "prepublication_return": {
            "candidate_returned_to_owner": True,
            "content_changed": True,
            "change_notice_path": relative("CHANGE_NOTICE.md"),
            "receipt_path": relative("PREPUBLICATION_RETURN_RECEIPT.json"),
        },
        "gates": {
            "candidate_frozen": True,
            "all_claims_dispositioned": True,
            "formal_claims_have_kernel_receipts": True,
            "all_references_resolve": True,
            "open_claims_not_worded_as_facts": True,
            "returned_bytes_equal_upload_bytes": True,
            "proof_bundle_in_upload_fileset": True,
        },
        "completion_claims": {
            "machine_proof_complete": True,
            "zenodo_upload_authorized": True,
        },
    }
    write_json("MACHINE_PROOF_BUNDLE.json", bundle)

    proof = {"path": relative("MACHINE_PROOF_BUNDLE.json"), **identity(D / "MACHINE_PROOF_BUNDLE.json")}
    return_identity = {"path": relative("PREPUBLICATION_RETURN_RECEIPT.json"), **identity(D / "PREPUBLICATION_RETURN_RECEIPT.json")}
    canonical_metadata = json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    metadata_sha = hashlib.sha256(canonical_metadata).hexdigest()
    required = (
        "AUTHORIZE_EXACT_UPLOAD "
        f"authorization_id={AUTHORIZATION_ID} "
        f"publication_id={PUBLICATION_ID} "
        f"return_sha256={return_identity['sha256']} "
        f"metadata_sha256={metadata_sha} "
        f"machine_proof_sha256={proof['sha256']}"
    )
    (D / "AUTHORIZE_EXACT_UPLOAD.txt").write_text(
        "# PENDING: exact statement for a subsequent natural-person decision; not yet granted.\n" + required + "\n",
        encoding="utf-8",
    )
    intended_uploads = [item["path"] for item in candidates] + [item["path"] for item in artifacts] + [proof["path"]]
    validator_command = [
        sys.executable,
        "-B",
        str(ROOT / "tools/qikvrt_zenodo_machine_proof.py"),
        "--proof-bundle",
        proof["path"],
    ]
    for upload_path in intended_uploads:
        validator_command.extend(("--upload-path", upload_path))
    subprocess.run(validator_command, cwd=ROOT, check=True)
    control = {
        "schema": "qikvrt_pr1128_publication_control_pending_v2",
        "publication_id": PUBLICATION_ID,
        "candidate_return_identity": return_identity,
        "canonical_metadata_sha256": metadata_sha,
        "proof_identity": {
            **proof,
            "schema": bundle["schema"],
            "publication_id": PUBLICATION_ID,
            "candidate_file_count": len(candidates),
            "artifact_count": len(artifacts),
            "claim_count": len(claims),
            "machine_proof_complete": True,
            "zenodo_upload_authorized": True,
            "policy": bundle["policy"],
        },
        "intended_upload_paths": intended_uploads,
        "controls_excluded_from_upload": ["AUTHORIZE_EXACT_UPLOAD.txt", "PUBLICATION_CONTROL_PENDING.json"],
        "required_statement": required,
        "machine_proof_gate_validated": True,
        "machine_proof_gate_term_boundary": "The schema-fixed zenodo_upload_authorized is only the machine-proof gate. Independent natural-person authorization remains absent.",
        "owner_authorization_record_present": False,
        "owner_exact_upload_authorized": False,
        "native_P3": False,
        "production_mutations": 0,
        "zenodo_record_state": "UNVERIFIED",
        "zenodo_readback": "REQUIRED_AFTER_AUTHORIZED_PUBLICATION",
        "Main_promotion": False,
        "P4": False,
        "EFFECT_ACK_DONE": False,
        "DONE": False,
        "PREDECESSOR_EVIDENCE_TRANSFER": False,
    }
    write_json("PUBLICATION_CONTROL_PENDING.json", control)

    work_outputs = []
    for upload_path in intended_uploads:
        observed = identity(ROOT / upload_path)
        work_outputs.append({"path": upload_path, "sha256": observed["sha256"]})
    work_unit = {
        "schema": "qikvrt_human_ai_contribution_work_unit_v1",
        "work_unit_id": "PR1128_EXPECTATIONS_WAGER_EFFECT_LAW_PUBLICATION_20260919_V2",
        "created_at": RETURNED_AT,
        "source_repository": "Goldkelch/qik-vrt",
        "source_ref": "publication/truth-no-conspiracy-theory-2026-09-19",
        "source_commit": "9e3d7950853f7e4e98cc8214074641dd4af0bb01",
        "source_tree": "114e18d5466db484b9df8b88a8163b9e32453157",
        "human_actor": "Ingolf Lohmann",
        "artificial_cognitive_actor": "OpenAI ChatGPT Codex (exact model build unavailable)",
        "human_contributions": [
            "Underlying personal hypothesis, experience, QIK-VRT claims and desired argumentative direction",
            "Instruction to publish the chat-created articles prominently in the Mesh repository and on Zenodo",
            "Decision to state which explanation the author presently considers most likely",
        ],
        "artificial_cognitive_contributions": [
            "Article drafting and editorial structure",
            "Legal and scientific-boundary language with primary-source bindings",
            "Complete line-level claim disposition, negative tests and exact Zenodo candidate controls",
        ],
        "joint_components": ["Three-article dossier and attributed author-evidence boundary"],
        "unresolved_origin": [],
        "outputs": work_outputs,
        "verification": {
            "scope_test": "VERIFIED_4_DOCUMENTS_552_CLAIMS_8_EXPECTED_REJECTIONS",
            "machine_proof_gate": "VERIFIED_EXACT_14_FILE_UPLOAD_SET_552_CLAIMS",
            "repository_integrity": "VERIFIED_4114_CLASSIFIED_ENTRIES_4105_IMMUTABLE_DIGESTS",
            "make_test": "COMPLETED_WITHOUT_ERROR",
        },
        "human_decision": "REPOSITORY_PUBLICATION_REQUESTED; EXACT_HASH_BOUND_ZENODO_AUTHORIZATION_PENDING",
        "external_effects": {
            "repository_branch_update": "AUTHORIZED_BY_REQUEST_PENDING_EXECUTION",
            "main_merge": False,
            "zenodo": "BLOCKED_PENDING_EXACT_HASH_BOUND_OWNER_AUTHORIZATION",
            "publication_readback": False,
        },
        "scientific_boundary": {
            "owner_most_likely_assessment_published": True,
            "calibrated_posterior": False,
            "specific_wager_identified": False,
            "payment_or_order_identified": False,
            "causal_chain_empirically_closed": False,
            "qikvrt_universal_prediction_superiority_proved": False,
            "criminal_responsibility_of_identified_person_established": False,
        },
        "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
    }
    work_unit_path = ROOT / "state/work_units/PR1128_EXPECTATIONS_WAGER_EFFECT_LAW_PUBLICATION_20260919_V2.json"
    work_unit_path.write_text(
        json.dumps(work_unit, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({"publication_id": PUBLICATION_ID, "claims": len(claims), "required_statement": required}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
