            if exc.code in (301, 302, 303, 307, 308):
                location = exc.headers.get("Location")
            else:
                detail = exc.read().decode("utf-8", errors="replace")[:2000]
                raise OrchestratorBlock(
                    f"artifact download endpoint returned {exc.code}: {detail}"
                ) from exc
        if not location:
            raise OrchestratorBlock("artifact download endpoint returned no safe redirect")
        original_host = urllib.parse.urlsplit(url).netloc
        target = urllib.parse.urlsplit(location)
        if target.scheme != "https" or not target.netloc or target.netloc == original_host:
            raise OrchestratorBlock("artifact redirect target is not an external HTTPS blob URL")
        plain = urllib.request.Request(
            location,
            method="GET",
            headers={"User-Agent": "qikvrt-autonomous-orchestrator-v2/1.0"},
        )
        try:
            with urllib.request.urlopen(plain, timeout=self.timeout) as response:
                destination.write_bytes(response.read())
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            raise OrchestratorBlock(f"artifact blob download failed: {exc}") from exc

    def file_json(self, path: str, ref: str) -> dict[str, Any]:
        quoted = urllib.parse.quote(path, safe="/")
        value = self.json("GET", f"/contents/{quoted}?ref={urllib.parse.quote(ref, safe='')}")
        if not isinstance(value, Mapping) or value.get("encoding") != "base64":
            raise OrchestratorBlock(f"GitHub file response is malformed: {path}@{ref}")
        try:
            raw = base64.b64decode("".join(str(value["content"]).split()), validate=True)
            parsed = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
            raise OrchestratorBlock(f"GitHub file is not canonical JSON: {path}@{ref}") from exc
        if not isinstance(parsed, dict):
            raise OrchestratorBlock(f"GitHub JSON file is not an object: {path}@{ref}")
        return parsed


def safe_extract_zip(
    archive: pathlib.Path,
    destination: pathlib.Path,
    *,
    maximum_members: int,
    maximum_bytes: int,
) -> list[pathlib.Path]:
    destination.mkdir(parents=True, exist_ok=True)
    extracted: list[pathlib.Path] = []
    total = 0
    try:
        with zipfile.ZipFile(archive) as package:
            members = package.infolist()
            if not members or len(members) > maximum_members:
                raise OrchestratorBlock("artifact ZIP member count is outside the bound")
            for member in members:
                pure = pathlib.PurePosixPath(member.filename)
                if pure.is_absolute() or ".." in pure.parts or not pure.parts:
                    raise OrchestratorBlock(f"unsafe ZIP member path: {member.filename}")
                mode = (member.external_attr >> 16) & 0o170000
                if mode == 0o120000:
                    raise OrchestratorBlock(f"ZIP symlink is forbidden: {member.filename}")
                if member.is_dir():
                    continue
                total += member.file_size
                if total > maximum_bytes:
                    raise OrchestratorBlock("artifact ZIP expands beyond the byte bound")
                target = destination.joinpath(*pure.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with package.open(member) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
                extracted.append(target)
    except zipfile.BadZipFile as exc:
        raise OrchestratorBlock(f"artifact is not a valid ZIP: {archive}") from exc
    return sorted(extracted)


def verify_artifact_metadata(
    client: GitHubClient,
    *,
    artifact_id: int,
    expected_name: str,
    expected_digest: str,
    expected_run_id: int,
    expected_head_sha: str,
) -> Mapping[str, Any]:
    value = client.json("GET", f"/actions/artifacts/{artifact_id}")
    if not isinstance(value, Mapping):
        raise OrchestratorBlock("artifact metadata is not an object")
    if value.get("id") != artifact_id or value.get("name") != expected_name:
        raise OrchestratorBlock("artifact identity mismatch")
    if value.get("expired") is not False:
        raise OrchestratorBlock("artifact is expired")
    digest = value.get("digest")
    if digest != f"sha256:{expected_digest}":
        raise OrchestratorBlock("artifact metadata digest mismatch")
    workflow = value.get("workflow_run", {})
    if workflow.get("id") != expected_run_id or workflow.get("head_sha") != expected_head_sha:
        raise OrchestratorBlock("artifact workflow binding mismatch")
    return value


def verify_source_binding(
    client: GitHubClient,
    *,
    pr_number: int,
    head_sha: str,
    tree_sha: str | None = None,
) -> Mapping[str, Any]:
    pr = client.json("GET", f"/pulls/{pr_number}")
    if not isinstance(pr, Mapping):
        raise OrchestratorBlock("source pull request response is malformed")
    if pr.get("head", {}).get("sha") != head_sha:
        raise OrchestratorBlock(f"source PR #{pr_number} head moved")
    commit = client.json("GET", f"/git/commits/{head_sha}")
    if not isinstance(commit, Mapping):
        raise OrchestratorBlock("source commit response is malformed")
    if tree_sha is not None and commit.get("tree", {}).get("sha") != tree_sha:
        raise OrchestratorBlock("source tree binding mismatch")
    return pr


def fetch_source_path(head_sha: str, relative: str) -> None:
    require_sha(head_sha, HEX40, "source head")
    result = run(("git", "fetch", "--no-tags", "origin", head_sha), timeout=300)
    if result.returncode:
        raise OrchestratorBlock(result.stderr.strip() or "cannot fetch source head")
    checkout = run(("git", "checkout", head_sha, "--", relative), timeout=300)
    if checkout.returncode:
        raise OrchestratorBlock(
            checkout.stderr.strip() or f"cannot materialize {relative} from source head"
        )


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise OrchestratorBlock(f"{label}: expected one replacement target, found {count}")
    return text.replace(old, new, 1)


def update_qce_status(directory: pathlib.Path, run_id: int, receipt_digest: str) -> None:
    readme = directory / "README.md"
    text = readme.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "| Lean-Ausführung dieses Kandidaten | `PENDING_REPOSITORY_RUN` |",
        "| Lean-Ausführung dieses Kandidaten | `KERNEL_EXECUTED_FORMAL_MODEL_CANDIDATE` — 36/36 Theoreme |",
        "QCE README Lean state",
    )
    text = replace_once(
        text,
        "| Axiom-Audit | Quellkandidat vorbereitet, nicht ausgeführt |",
        "| Axiom-Audit | 36/36 `#print axioms` ausgeführt; keine projektlokalen Axiome |",
        "QCE README axiom state",
    )
    text = replace_once(
        text,
        "`LEAN_EXECUTION = PENDING_REPOSITORY_RUN`",
        "`LEAN_EXECUTION = KERNEL_EXECUTED_FORMAL_MODEL_CANDIDATE`",
        "QCE README final state",
    )
    marker = "`PHYSICAL_CORRESPONDENCE = OPEN_CANDIDATE`"
    if "QCE_KERNEL_RECEIPT.json" not in text:
        insertion = (
            f"`KERNEL_RECEIPT = QCE_KERNEL_RECEIPT.json`  \n"
            f"`KERNEL_RUN_ID = {run_id}`  \n"
            f"`KERNEL_ARTIFACT_ZIP_SHA256 = {receipt_digest}`  \n\n"
        )
        text = replace_once(text, marker, insertion + marker, "QCE README receipt insertion")
    readme.write_text(text, encoding="utf-8")

    claims_path = directory / "CLAIM_MATRIX.json"
    claims = load_json(claims_path, "QCE claim matrix")
    execution = claims.get("formal_execution")
    if not isinstance(execution, MutableMapping):
        raise OrchestratorBlock("QCE claim matrix formal_execution is absent")
    execution.update(
        {
            "lean_executed_for_this_candidate": True,
            "receipt_state": "KERNEL_EXECUTED_FORMAL_MODEL_CANDIDATE",
            "kernel_receipt": "QCE_KERNEL_RECEIPT.json",
            "axiom_output": "qce-axiom-output.txt",
            "verification_output": "qce-verification.json",
            "workflow_run_id": run_id,
        }
    )
    for claim in claims.get("claims", []):
        if claim.get("id") == "QCE-C05":
            claim["boundary"] = (
                "Lean execution is established for the exact finite model source; "
                "model order is not thereby a physical-time theorem."
            )
        if claim.get("id") == "QCE-C12":
            claim["boundary"] = (
                "Kernel execution is established for this finite source; physical "
