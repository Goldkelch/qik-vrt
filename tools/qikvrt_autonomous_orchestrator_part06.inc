        (sys.executable, "-B", str(directory / "regenerate_qce_integrity.py")),
        cwd=directory,
        timeout=120,
        check=True,
    )
    return {
        "handler": unit["handler"],
        "source_pr": source_pr,
        "source_head": source_head,
        "source_tree": source_tree,
        "kernel_run_id": run_id,
        "kernel_artifact_id": artifact_id,
        "kernel_artifact_sha256": artifact_digest,
        "kernel_state": "KERNEL_EXECUTED_FORMAL_MODEL_CANDIDATE",
        "accepted_theorems": 36,
        "axiom_audit_directives": 36,
        "physical_correspondence": "OPEN_CANDIDATE",
        "regeneration": regeneration.stdout.strip(),
    }


# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
# QIK-VRT autonomous orchestrator source continuation 3/4.
def find_single(directory: pathlib.Path, pattern: str, label: str) -> pathlib.Path:
    matches = sorted(directory.rglob(pattern))
    if len(matches) != 1:
        raise OrchestratorBlock(f"{label}: expected one file, found {len(matches)}")
    return matches[0]


def validate_audio_artifact(
    extracted: pathlib.Path,
    expected: Mapping[str, Any],
    *,
    repository: str,
    run_id: int,
    carrier_sha: str,
) -> dict[str, Any]:
    audio_id = str(expected["audio_id"])
    receipt_path = find_single(extracted, "chunk-materialization-receipt.json", f"{audio_id} receipt")
    observation_path = find_single(extracted, "normalization-observation.json", f"{audio_id} observation")
    transcript_txt = find_single(extracted, "*.transcript.txt", f"{audio_id} transcript text")
    transcript_json = find_single(extracted, "*.transcript.json", f"{audio_id} transcript JSON")
    provenance_path = find_single(extracted, "*.provenance.json", f"{audio_id} provenance")
    receipt = load_json(receipt_path, f"{audio_id} materialization receipt")
    observation = load_json(observation_path, f"{audio_id} normalization observation")
    structured = load_json(transcript_json, f"{audio_id} structured transcript")
    provenance = load_json(provenance_path, f"{audio_id} provenance")
    if receipt.get("schema") != "qikvrt_audio_chunk_materialization_receipt_v1":
        raise OrchestratorBlock(f"{audio_id} receipt schema mismatch")
    if receipt.get("repository") != repository or observation.get("repository") != repository:
        raise OrchestratorBlock(f"{audio_id} repository binding mismatch")
    if receipt.get("audio_id") != audio_id or observation.get("audio_id") != audio_id:
        raise OrchestratorBlock(f"{audio_id} identity mismatch")
    if receipt.get("carrier_sha") != carrier_sha or observation.get("carrier_sha") != carrier_sha:
        raise OrchestratorBlock(f"{audio_id} carrier binding mismatch")
    if observation.get("run_id") != run_id:
        raise OrchestratorBlock(f"{audio_id} run binding mismatch")
    if receipt.get("original", {}).get("sha256") != expected["original_sha256"]:
        raise OrchestratorBlock(f"{audio_id} original digest mismatch")
    if receipt.get("derivative", {}).get("sha256") != expected["derivative_sha256"]:
        raise OrchestratorBlock(f"{audio_id} derivative digest mismatch")
    if observation.get("original_sha256") != expected["original_sha256"]:
        raise OrchestratorBlock(f"{audio_id} observation original digest mismatch")
    if observation.get("derivative_sha256") != expected["derivative_sha256"]:
        raise OrchestratorBlock(f"{audio_id} observation derivative digest mismatch")
    if observation.get("automatic_asr") != "COMPLETE":
        raise OrchestratorBlock(f"{audio_id} automatic ASR is not complete")
    if observation.get("human_acoustic_review") != "PENDING":
        raise OrchestratorBlock(f"{audio_id} human review boundary changed")
    if observation.get("verbatim_verified") is not False:
        raise OrchestratorBlock(f"{audio_id} falsely claims verbatim verification")
    if observation.get("zenodo_mutation") is not False:
        raise OrchestratorBlock(f"{audio_id} falsely claims or performs Zenodo mutation")
    outputs = {item["filename"]: item for item in observation.get("outputs", [])}
    for path in (transcript_txt, transcript_json, provenance_path):
        item = outputs.get(path.name)
        if not isinstance(item, Mapping):
            raise OrchestratorBlock(f"{audio_id} output inventory lacks {path.name}")
        if item.get("bytes") != path.stat().st_size or item.get("sha256") != sha256_file(path):
            raise OrchestratorBlock(f"{audio_id} output binding mismatch: {path.name}")
    if provenance.get("input", {}).get("sha256") != expected["derivative_sha256"]:
        raise OrchestratorBlock(f"{audio_id} provenance derivative mismatch")
    if structured.get("text") != transcript_txt.read_text(encoding="utf-8").strip():
        raise OrchestratorBlock(f"{audio_id} structured/plain transcript mismatch")
    segments = structured.get("segments")
    if not isinstance(segments, list) or not segments:
        raise OrchestratorBlock(f"{audio_id} structured transcript has no segments")
    return {
        "audio_id": audio_id,
        "semantic_label": expected["semantic_label"],
        "original_sha256": expected["original_sha256"],
        "derivative_sha256": expected["derivative_sha256"],
        "transcript_sha256": sha256_file(transcript_txt),
        "structured_sha256": sha256_file(transcript_json),
        "provenance_sha256": sha256_file(provenance_path),
        "materialization_receipt_sha256": sha256_file(receipt_path),
        "normalization_observation_sha256": sha256_file(observation_path),
        "segment_count": len(segments),
        "automatic_asr": "COMPLETE",
        "human_acoustic_review": "PENDING",
        "verbatim_verified": False,
        "scientific_validation": "NOT_PERFORMED",
        "transcript_files": {
            "plain": transcript_txt.name,
            "structured": transcript_json.name,
            "provenance": provenance_path.name,
            "materialization_receipt": receipt_path.name,
            "normalization_observation": observation_path.name,
        },
    }


def handler_audio_ingest(
    unit: Mapping[str, Any], contract: Mapping[str, Any], client: GitHubClient
) -> dict[str, Any]:
    inputs = unit["inputs"]
    source_head = require_sha(inputs.get("source_head"), HEX40, "audio source head")
    source_pr = int(inputs.get("source_pr"))
    run_id = int(inputs.get("run_id"))
    carrier_sha = require_sha(inputs.get("carrier_sha"), HEX40, "audio carrier SHA")
    output_root = ROOT / str(inputs.get("output_root"))
    verify_source_binding(client, pr_number=source_pr, head_sha=source_head)
    output_root.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    artifacts_index: list[dict[str, Any]] = []
    for expected in inputs.get("artifacts", []):
        audio_id = str(expected["audio_id"])
        artifact_id = int(expected["artifact_id"])
        artifact_name = str(expected["artifact_name"])
        artifact_digest = require_sha(
            expected.get("artifact_sha256"), HEX64, f"{audio_id} artifact digest"
        )
        verify_artifact_metadata(
            client,
            artifact_id=artifact_id,
            expected_name=artifact_name,
            expected_digest=artifact_digest,
            expected_run_id=run_id,
            expected_head_sha=source_head,
        )
        with tempfile.TemporaryDirectory(prefix=f"qikvrt-{audio_id}-artifact-") as temp:
            tempdir = pathlib.Path(temp)
            archive = tempdir / "artifact.zip"
            client.download_artifact(artifact_id, archive)
            if sha256_file(archive) != artifact_digest:
                raise OrchestratorBlock(f"{audio_id} downloaded artifact digest mismatch")
            extracted = tempdir / "extracted"
            safe_extract_zip(
                archive,
                extracted,
                maximum_members=int(contract["limits"]["maximum_zip_members"]),
                maximum_bytes=int(contract["limits"]["maximum_artifact_bytes"]),
            )
            record = validate_audio_artifact(
                extracted,
                expected,
                repository=str(contract["authority_repository"]),
                run_id=run_id,
                carrier_sha=carrier_sha,
            )
            destination = output_root / audio_id
            if destination.exists():
                shutil.rmtree(destination)
            destination.mkdir(parents=True)
            archive_name = f"{artifact_name}.zip"
            shutil.copy2(archive, destination / archive_name)
            for path in sorted(extracted.rglob("*")):
                if path.is_file():
                    shutil.copy2(path, destination / path.name)
