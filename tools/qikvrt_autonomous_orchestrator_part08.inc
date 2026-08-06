            },
            {
                "id": "ONTOLOGY-U05",
                "state": "WAITING_EMPIRICAL",
                "scope": "independent_reproduction",
                "closure_condition": "Independent groups reproduce formal, numerical and measurement results.",
            },
        ]
    )
    write_json(
        output_root / "OPEN_OBLIGATIONS.json",
        {
            "schema": "qikvrt_unified_ontology_open_obligations_v1",
            "obligations": obligations,
            "physical_closure": "OPEN",
            "empirical_confirmation": "OPEN",
        },
    )
    lean = """/--\nSPDX-License-Identifier: PolyForm-Noncommercial-1.0.0\nCopyright 2026 Ingolf Lohmann.\n-/\n\nnamespace QIKVRT.UnifiedOntology\n\ninductive Stage where\n  | difference | information | relation | causality | spacetime\n  | appearance | life | cognition | responsibility | future\n  deriving DecidableEq, Repr\n\ndef ordinal : Stage → Nat\n  | .difference => 0 | .information => 1 | .relation => 2\n  | .causality => 3 | .spacetime => 4 | .appearance => 5\n  | .life => 6 | .cognition => 7 | .responsibility => 8 | .future => 9\n\ndef next : Stage → Option Stage\n  | .difference => some .information | .information => some .relation\n  | .relation => some .causality | .causality => some .spacetime\n  | .spacetime => some .appearance | .appearance => some .life\n  | .life => some .cognition | .cognition => some .responsibility\n  | .responsibility => some .future | .future => none\n\ntheorem next_increases {a b : Stage} (h : next a = some b) : ordinal b = ordinal a + 1 := by\n  cases a <;> simp [next, ordinal] at h ⊢ <;> cases h <;> rfl\n\ntheorem future_is_terminal : next .future = none := rfl\n\ntheorem difference_starts_at_zero : ordinal .difference = 0 := rfl\n\nstructure ClosureWitness where\n  formalRoot : Bool\n  physicalCorrespondence : Bool\n  differentiatingPrediction : Bool\n  empiricalSupport : Bool\n  independentReproduction : Bool\n\ndef massiveSphere (w : ClosureWitness) : Bool :=\n  w.formalRoot && w.physicalCorrespondence && w.differentiatingPrediction &&\n  w.empiricalSupport && w.independentReproduction\n\ndef currentWitness : ClosureWitness :=\n  { formalRoot := false, physicalCorrespondence := false,\n    differentiatingPrediction := false, empiricalSupport := false,\n    independentReproduction := false }\n\ntheorem current_not_massive : massiveSphere currentWitness = false := rfl\n\nend QIKVRT.UnifiedOntology\n"""
    (output_root / "UnifiedOntology.lean").write_text(lean, encoding="utf-8")
    audit = """/--\nSPDX-License-Identifier: PolyForm-Noncommercial-1.0.0\nCopyright 2026 Ingolf Lohmann.\n-/\nimport «UnifiedOntology»\n#print axioms QIKVRT.UnifiedOntology.next_increases\n#print axioms QIKVRT.UnifiedOntology.future_is_terminal\n#print axioms QIKVRT.UnifiedOntology.difference_starts_at_zero\n#print axioms QIKVRT.UnifiedOntology.current_not_massive\n"""
    (output_root / "UnifiedOntology_AxiomAudit.lean").write_text(audit, encoding="utf-8")
    (output_root / "lean-toolchain").write_text("leanprover/lean4:v4.19.0\n", encoding="utf-8")
    (output_root / "lakefile.lean").write_text(
        "import Lake\nopen Lake DSL\npackage qikvrtUnifiedOntology where\nlean_lib UnifiedOntology\n",
        encoding="utf-8",
    )
    roadmap = [
        "<!--",
        "SPDX-License-Identifier: CC-BY-NC-ND-4.0",
        "Copyright 2026 Ingolf Lohmann.",
        "-->",
        "",
        "# Vereinheitlichter Ontologiekern — formales Arbeitsprogramm",
        "",
        "Dieses Paket typisiert die Kette",
        "",
        "`Unterschied → Information → Relation → Kausalität → Raumzeit → Erscheinung → Leben → Kognition → Verantwortung → Zukunft`",
        "",
        "ohne eine Benennung bereits als Herleitung auszugeben. Der Lean-Kern beweist nur die endliche Reihenfolge und die gegenwärtige Nichtschließung des deklarierten Statusmodells.",
        "",
        "## Nächste maschinenbearbeitbare Schritte",
        "",
        "1. Für jede Kante Definition, Annahme, formalen Satz, Korrespondenzpostulat, empirischen Anspruch, Interpretation und normative Regel trennen.",
        "2. Bestehende finite Lean-Kerne über explizite Imports und Voraussetzungen anbinden.",
        "3. Zirkularitäts-, Redundanz- und Konsistenzprüfungen materialisieren.",
        "4. Für QCE-O01 bis QCE-O07 ausführbare Modell- und Messprotokolle erstellen.",
        "5. Vor entscheidenden Daten mindestens eine unterscheidende Vorhersage und ihren Falsifikator einfrieren.",
        "",
        "## Nicht automatisierbare Grenzen",
        "",
        "Menschliche akustische Zertifizierung, reale Messungen, unabhängige Replikation und irreversible Publikation benötigen jeweils die ausdrücklich ausgewiesene externe Evidenz oder Autorisierung.",
        "",
        "`UNIFIED_ONTOLOGY_KERNEL = MODEL_PROGRAM_OPEN`  ",
        "`PHYSICAL_CORRESPONDENCE = OPEN_CANDIDATE`  ",
        "`EMPIRICAL_CONFIRMATION = OPEN`  ",
        "`PASS = NOT_CLAIMED`  ",
        "`FINAL_PASS = NOT_CLAIMED`  ",
        "`EFFECT_ACK_DONE = NOT_CLAIMED`",
        "",
    ]
    (output_root / "ROADMAP.md").write_text("\n".join(roadmap), encoding="utf-8")
    return {
        "handler": unit["handler"],
        "chain_nodes": len(nodes),
        "chain_edges": len(edges),
        "open_obligations": len(obligations),
        "formal_status": "FINITE_STATUS_MODEL_PREPARED",
        "unified_ontology_proof": "OPEN",
        "physical_correspondence": "OPEN_CANDIDATE",
        "empirical_confirmation": "OPEN",
    }


# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
# QIK-VRT autonomous orchestrator source continuation 4/4.
def handler_close_superseded(
    unit: Mapping[str, Any], contract: Mapping[str, Any], client: GitHubClient
) -> dict[str, Any]:
    inputs = unit["inputs"]
    closed: list[dict[str, Any]] = []
    for number in inputs["pull_requests"]:
        required_title = inputs["required_titles"][str(number)]
        pr = client.json("GET", f"/pulls/{number}")
        if not isinstance(pr, Mapping) or pr.get("title") != required_title:
            raise OrchestratorBlock(f"PR #{number} identity/title mismatch")
        if pr.get("merged_at") is not None:
            raise OrchestratorBlock(f"PR #{number} was merged and cannot be classified transport-only")
        previous = pr.get("state")
        if previous == "open":
            updated = client.json(
                "PATCH", f"/pulls/{number}", payload={"state": "closed"}
            )
            if not isinstance(updated, Mapping) or updated.get("state") != "closed":
                raise OrchestratorBlock(f"PR #{number} closure did not persist")
        elif previous != "closed":
            raise OrchestratorBlock(f"PR #{number} has unexpected state {previous}")
        closed.append(
            {
                "number": number,
                "title": required_title,
                "previous_state": previous,
                "state": "closed",
                "merged": False,
                "reason": inputs["closure_reason"],
            }
        )
    return {
        "handler": unit["handler"],
        "repository": contract["authority_repository"],
        "closed_without_merge": closed,
        "external_effect": "NONE",
    }


HANDLERS = {
    "QCE_FINALIZE": handler_qce_finalize,
    "AUDIO_ASR_INGEST": handler_audio_ingest,
    "ONTOLOGY_RESEARCH_PROGRAM": handler_ontology_program,
    "CLOSE_SUPERSEDED_PRS": handler_close_superseded,
}


def find_unit(queue: Mapping[str, Any], identifier: str) -> MutableMapping[str, Any]:
    matches = [unit for unit in queue["work_units"] if unit["id"] == identifier]
    if len(matches) != 1 or not isinstance(matches[0], MutableMapping):
        raise OrchestratorBlock(f"work unit not uniquely found: {identifier}")
    return matches[0]


def materialize_receipt(
    unit: Mapping[str, Any],
    *,
    base_sha: str,
    branch: str,
    result: Mapping[str, Any],
) -> pathlib.Path:
    RECEIPT_ROOT.mkdir(parents=True, exist_ok=True)
    path = RECEIPT_ROOT / f"{unit['id'].lower()}.json"
    value = {
        "schema": "qikvrt_autonomous_work_unit_candidate_receipt_v2",
        "work_unit_id": unit["id"],
        "handler": unit["handler"],
        "effect_class": unit["effect_class"],
        "state": "CANDIDATE_MATERIALIZED_PENDING_EXPECTED_HEAD_PROMOTION",
        "observed_base_sha": base_sha,
        "candidate_branch": branch,
        "handler_result": result,
        "external_effect": "NONE",
        "promotion_conditions": list(PROMOTION_CONDITIONS),
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
