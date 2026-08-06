                "correspondence and empirical corroboration remain open."
            )
    require_false_claims(claims.get("release_claims"), "QCE claim matrix")
    write_json(claims_path, claims)

    bundle_path = directory / "MACHINE_PROOF_BUNDLE.json"
    bundle = load_json(bundle_path, "QCE machine-proof bundle")
    bundle.setdefault("formalization", {})["status"] = "KERNEL_EXECUTED_FORMAL_MODEL_CANDIDATE"
    bundle.setdefault("receipt", {}).update(
        {
            "executed_receipt": "QCE_KERNEL_RECEIPT.json",
            "axiom_output": "qce-axiom-output.txt",
            "verification_output": "qce-verification.json",
            "workflow_run_id": run_id,
            "required_before_zenodo_publication": True,
        }
    )
    bundle["physical_correspondence"] = "OPEN_CANDIDATE"
    require_false_claims(
        {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
        },
        "QCE machine-proof bundle",
    )
    write_json(bundle_path, bundle)


def verify_qce_receipt(
    receipt: Mapping[str, Any],
    verification: Mapping[str, Any],
    *,
    source_head: str,
    source_tree: str,
    run_id: int,
    run_attempt: int,
) -> None:
    if receipt.get("schema") != "qikvrt-qce-kernel-receipt/1.0":
        raise OrchestratorBlock("QCE receipt schema mismatch")
    if receipt.get("state") != "KERNEL_EXECUTED_FORMAL_MODEL_CANDIDATE":
        raise OrchestratorBlock("QCE receipt does not establish executed finite-model state")
    require_false_claims(receipt.get("completion_claims"), "QCE receipt")
    source = receipt.get("source_binding", {})
    if source.get("repository") != "Goldkelch/qik-vrt":
        raise OrchestratorBlock("QCE receipt repository mismatch")
    if source.get("commit") != source_head or source.get("tree") != source_tree:
        raise OrchestratorBlock("QCE receipt source binding mismatch")
    workflow = receipt.get("workflow_binding", {})
    if str(workflow.get("run_id")) != str(run_id) or str(workflow.get("run_attempt")) != str(run_attempt):
        raise OrchestratorBlock("QCE receipt workflow binding mismatch")
    kernel = receipt.get("kernel_execution", {})
    exact = {
        "accepted_theorems": 36,
        "axiom_audit_directives": 36,
        "named_theorems": 36,
        "project_axioms": 0,
        "sorry_or_admit": 0,
        "unsafe_declarations": 0,
    }
    for key, expected in exact.items():
        if kernel.get(key) != expected:
            raise OrchestratorBlock(f"QCE receipt {key} mismatch")
    formal = receipt.get("formal_scope", {})
    if formal.get("finite_model_contract_kernel_accepted") is not True:
        raise OrchestratorBlock("QCE finite-model kernel acceptance is absent")
    if formal.get("physical_closure") is not False or formal.get("physical_correspondence_established") is not False:
        raise OrchestratorBlock("QCE receipt overclaims physical closure")
    if verification.get("result") != "FORMAL_MODEL_VERIFIED":
        raise OrchestratorBlock("QCE verification result mismatch")
    if verification.get("physical_correspondence") != "OPEN_CANDIDATE":
        raise OrchestratorBlock("QCE verification promoted physical correspondence")
    require_false_claims(
        {key: verification.get(key) for key in ("PASS", "FINAL_PASS", "EFFECT_ACK_DONE")},
        "QCE verification",
    )


def update_publication_indexes(source_path: str) -> None:
    machine_path = ROOT / "docs/publications/index.json"
    machine = load_json(machine_path, "publication machine index")
    bundles = machine.get("publication_bundles")
    if not isinstance(bundles, list):
        raise OrchestratorBlock("publication bundle index is absent")
    readme_path = f"{source_path}/README.md"
    matching = [item for item in bundles if item.get("path") == readme_path]
    entry = {
        "id": "qikvrt-quantum-causal-emergence-v1",
        "title": "QIK-VRT Quantum Causal Emergence — endliches formales Modell",
        "path": readme_path,
        "state": "repository_candidate_formal_model_verified_physical_correspondence_open",
    }
    if len(matching) > 1:
        raise OrchestratorBlock("QCE publication index entry is duplicated")
    if matching:
        matching[0].update(entry)
    else:
        bundles.append(entry)
    write_json(machine_path, machine)

    human_path = ROOT / "docs/publications/index.html"
    html = human_path.read_text(encoding="utf-8")
    if readme_path not in html:
        lines = html.splitlines()
        target = next(
            (
                index
                for index, line in enumerate(lines)
                if "2026-08-04-pre-spacetime-ontology/README.md" in line
            ),
            None,
        )
        if target is None:
            raise OrchestratorBlock("human publication index insertion anchor is absent")
        row = (
            '        <a class="collection-row" '
            'href="https://github.com/Goldkelch/qik-vrt/blob/main/'
            f'{readme_path}"><time>05.08.</time><span><strong>'
            'Quantum Causal Emergence (QCE)</strong><small>36/36 Lean-Modelltheoreme; '
            'physikalische Korrespondenz offen</small></span><b>Öffnen →</b></a>'
        )
        lines.insert(target + 1, row)
        human_path.write_text("\n".join(lines) + ("\n" if html.endswith("\n") else ""), encoding="utf-8")


def handler_qce_finalize(
    unit: Mapping[str, Any], contract: Mapping[str, Any], client: GitHubClient
) -> dict[str, Any]:
    inputs = unit["inputs"]
    source_head = require_sha(inputs.get("source_head"), HEX40, "QCE source head")
    source_tree = require_sha(inputs.get("source_tree"), HEX40, "QCE source tree")
    source_path = str(inputs.get("source_path"))
    source_pr = int(inputs.get("source_pr"))
    run_id = int(inputs.get("kernel_run_id"))
    run_attempt = int(inputs.get("kernel_run_attempt"))
    artifact_id = int(inputs.get("kernel_artifact_id"))
    artifact_name = str(inputs.get("kernel_artifact_name"))
    artifact_digest = require_sha(
        inputs.get("kernel_artifact_sha256"), HEX64, "QCE artifact digest"
    )
    verify_source_binding(
        client,
        pr_number=source_pr,
        head_sha=source_head,
        tree_sha=source_tree,
    )
    verify_artifact_metadata(
        client,
        artifact_id=artifact_id,
        expected_name=artifact_name,
        expected_digest=artifact_digest,
        expected_run_id=run_id,
        expected_head_sha=source_head,
    )
    fetch_source_path(source_head, source_path)
    directory = ROOT / source_path
    if not directory.is_dir():
        raise OrchestratorBlock("QCE source directory was not materialized")
    with tempfile.TemporaryDirectory(prefix="qikvrt-qce-artifact-") as temp:
        tempdir = pathlib.Path(temp)
        archive = tempdir / "artifact.zip"
        client.download_artifact(artifact_id, archive)
        if sha256_file(archive) != artifact_digest:
            raise OrchestratorBlock("QCE downloaded artifact digest mismatch")
        extracted = tempdir / "extracted"
        safe_extract_zip(
            archive,
            extracted,
            maximum_members=int(contract["limits"]["maximum_zip_members"]),
            maximum_bytes=int(contract["limits"]["maximum_artifact_bytes"]),
        )
        expected = {
            "QCE_KERNEL_RECEIPT.json",
            "qce-axiom-output.txt",
            "qce-verification.json",
        }
        actual = {path.relative_to(extracted).as_posix() for path in extracted.rglob("*") if path.is_file()}
        if actual != expected:
            raise OrchestratorBlock(f"QCE artifact fileset mismatch: {sorted(actual)}")
        receipt = load_json(extracted / "QCE_KERNEL_RECEIPT.json", "QCE executed receipt")
        verification = load_json(extracted / "qce-verification.json", "QCE verification")
        axiom_bytes = (extracted / "qce-axiom-output.txt").read_bytes()
        if sha256_bytes(axiom_bytes) != receipt["kernel_execution"]["axiom_output_sha256"]:
            raise OrchestratorBlock("QCE axiom output digest mismatch")
        if sha256_file(extracted / "qce-verification.json") != receipt["kernel_execution"]["verification_output_sha256"]:
            raise OrchestratorBlock("QCE verification output digest mismatch")
        verify_qce_receipt(
            receipt,
            verification,
            source_head=source_head,
            source_tree=source_tree,
            run_id=run_id,
            run_attempt=run_attempt,
        )
        for name in sorted(expected):
            shutil.copy2(extracted / name, directory / name)
    update_qce_status(directory, run_id, artifact_digest)
    update_publication_indexes(source_path)
    regeneration = run(
