            record["artifact_zip"] = archive_name
            record["artifact_zip_sha256"] = artifact_digest
            records.append(record)
            artifacts_index.append(
                {
                    "audio_id": audio_id,
                    "artifact_id": artifact_id,
                    "artifact_name": artifact_name,
                    "artifact_zip": f"{audio_id}/{archive_name}",
                    "artifact_zip_sha256": artifact_digest,
                    "run_id": run_id,
                    "source_head": source_head,
                    "carrier_sha": carrier_sha,
                }
            )
    records.sort(key=lambda item: item["audio_id"])
    write_json(
        output_root / "ARTIFACTS.json",
        {
            "schema": "qikvrt_audio_asr_artifact_index_v1",
            "repository": contract["authority_repository"],
            "source_pr": source_pr,
            "source_head": source_head,
            "run_id": run_id,
            "artifacts": artifacts_index,
            "boundary": {
                "automatic_asr": "COMPLETE",
                "human_acoustic_review": "PENDING",
                "verbatim_verified": False,
                "scientific_validation": "NOT_PERFORMED",
                "zenodo_mutation": False,
            },
        },
    )
    write_json(
        output_root / "REVIEW_MATRIX.json",
        {
            "schema": "qikvrt_audio_human_review_matrix_v1",
            "repository": contract["authority_repository"],
            "source_pr": source_pr,
            "source_head": source_head,
            "run_id": run_id,
            "items": records,
            "disposition": "WAITING_HUMAN_ACOUSTIC_REVIEW",
            "use_of_repository_text_twins": "CONTEXT_ONLY_NOT_VERBATIM_CERTIFICATION",
            "completion_claims": {
                "PASS": False,
                "FINAL_PASS": False,
                "EFFECT_ACK_DONE": False,
            },
        },
    )
    lines = [
        "<!--",
        "SPDX-License-Identifier: CC-BY-NC-ND-4.0",
        "Copyright 2026 Ingolf Lohmann.",
        "-->",
        "",
        "# A08/A09 — begrenzte Offline-ASR-Evidenz",
        "",
        f"Quelle: Authority PR #{source_pr}, Head `{source_head}`, Workflow-Lauf `{run_id}`.",
        "",
        "Die beiden GitHub-Artefakte wurden bytegenau übernommen, ihre ZIP-Digests sowie alle internen Quelle-, Derivat- und Ausgabedaten wurden geprüft. Die Dateien enthalten kein Roh-Audio.",
        "",
        "## Erkenntnisgrenze",
        "",
        "Die automatischen Transkripte sind **keine** akustisch bestätigten Wortlaute. Sie sind als rohe ASR-Beobachtung mit `human_acoustic_review = PENDING` und `verbatim_verified = false` persistiert. Inhaltliche oder wissenschaftliche Schlussfolgerungen dürfen daraus erst nach menschlicher akustischer Prüfung gezogen werden.",
        "",
        "## Items",
        "",
    ]
    for item in records:
        lines.extend(
            [
                f"### {item['audio_id'].upper()} — {item['semantic_label']}",
                "",
                f"- Original SHA-256: `{item['original_sha256']}`",
                f"- Derivat SHA-256: `{item['derivative_sha256']}`",
                f"- Transcript SHA-256: `{item['transcript_sha256']}`",
                f"- Segmente: `{item['segment_count']}`",
                "- Automatische ASR: `COMPLETE`",
                "- Menschliche akustische Prüfung: `PENDING`",
                "- Wortlaut bestätigt: `false`",
                "",
            ]
        )
    lines.extend(
        [
            "## Disposition",
            "",
            "`WAITING_HUMAN_ACOUSTIC_REVIEW`",
            "",
            "`ZENODO_MUTATION = false`",
            "",
            "`PASS = NOT_CLAIMED`  ",
            "`FINAL_PASS = NOT_CLAIMED`  ",
            "`EFFECT_ACK_DONE = NOT_CLAIMED`",
            "",
        ]
    )
    (output_root / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return {
        "handler": unit["handler"],
        "source_pr": source_pr,
        "source_head": source_head,
        "run_id": run_id,
        "artifact_count": len(records),
        "items": records,
        "disposition": "WAITING_HUMAN_ACOUSTIC_REVIEW",
        "verbatim_verified": False,
        "scientific_validation": "NOT_PERFORMED",
    }


def handler_ontology_program(
    unit: Mapping[str, Any], _contract: Mapping[str, Any], _client: GitHubClient
) -> dict[str, Any]:
    inputs = unit["inputs"]
    output_root = ROOT / str(inputs["output_root"])
    output_root.mkdir(parents=True, exist_ok=True)
    chain = list(inputs["chain"])
    if len(chain) < 2 or len(chain) != len(set(chain)):
        raise OrchestratorBlock("ontology chain is malformed")
    nodes = []
    kind_by_stage = {
        "difference": "primitive_or_axiom_candidate",
        "information": "definition_and_correspondence_obligation",
        "relation": "definition_and_formalization_obligation",
        "causality": "interpretive_and_physical_correspondence_obligation",
        "spacetime": "physical_correspondence_obligation",
        "appearance": "interpretive_obligation",
        "life": "empirical_and_definition_obligation",
        "cognition": "definition_empirical_and_recursive_model_obligation",
        "responsibility": "normative_obligation",
        "future": "normative_and_operational_obligation",
    }
    for index, stage in enumerate(chain):
        nodes.append(
            {
                "id": stage,
                "ordinal": index,
                "claim_kind": kind_by_stage.get(stage, "open_obligation"),
                "formal_status": "MODEL_PROGRAM_OPEN",
                "physical_status": "OPEN_CANDIDATE",
            }
        )
    edges = [
        {
            "from": chain[index],
            "to": chain[index + 1],
            "status": "OPEN_DERIVATION_OBLIGATION",
            "required_separation": [
                "definition",
                "formal_theorem",
                "correspondence_postulate",
                "empirical_claim",
                "interpretation",
                "normative_rule",
            ],
        }
        for index in range(len(chain) - 1)
    ]
    write_json(
        output_root / "CLAIM_TAXONOMY.json",
        {
            "schema": "qikvrt_unified_ontology_claim_taxonomy_v1",
            "author": "Ingolf Lohmann",
            "nodes": nodes,
            "allowed_claim_kinds": [
                "DEFINITION",
                "ASSUMPTION",
                "FORMAL_THEOREM",
                "CORRESPONDENCE_POSTULATE",
                "EMPIRICAL_CLAIM",
                "INTERPRETATION",
                "NORMATIVE_RULE",
            ],
            "boundary": "No stage transition is promoted merely by naming it.",
            "completion_claims": {
                "PASS": False,
                "FINAL_PASS": False,
                "EFFECT_ACK_DONE": False,
                "PHYSICAL_CLOSURE": False,
            },
        },
    )
    write_json(
        output_root / "DEPENDENCY_GRAPH.json",
        {
            "schema": "qikvrt_unified_ontology_dependency_graph_v1",
            "nodes": nodes,
            "edges": edges,
            "acyclic_by_construction": True,
            "graph_status": "FORMALIZATION_PROGRAM_NOT_ONTOLOGY_WIDE_PROOF",
        },
    )
    obligations = [
        {
            "id": identifier,
            "state": "OPEN",
            "scope": "physical_correspondence",
        }
        for identifier in inputs.get("open_physics_obligations", [])
    ]
    obligations.extend(
        [
            {
                "id": "ONTOLOGY-U01",
                "state": "OPEN",
                "scope": "unified_non_circular_axiomatization",
                "closure_condition": "One typed root imports every finite formal core and exposes every extra assumption.",
            },
            {
                "id": "ONTOLOGY-U02",
                "state": "OPEN",
                "scope": "edge_by_edge_derivation",
                "closure_condition": "Each chain edge is classified and either proved, postulated, measured, interpreted or normatively declared.",
            },
            {
                "id": "ONTOLOGY-U03",
                "state": "WAITING_HUMAN",
                "scope": "audio_verbatim_review",
                "closure_condition": "A08 and A09 receive line-by-line acoustic review or explicit unresolved markings.",
            },
            {
                "id": "ONTOLOGY-U04",
                "state": "WAITING_EMPIRICAL",
                "scope": "distinguishing_prediction",
                "closure_condition": "At least one preregistered quantitative prediction distinguishes the model from named alternatives.",
