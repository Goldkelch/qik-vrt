            raise OrchestratorBlock(f"work unit {identifier} has missing dependencies: {missing}")
    validate_acyclic(index)
    require_false_claims(queue.get("completion_claims"), "work queue")
    return index


def validate_acyclic(index: Mapping[str, Mapping[str, Any]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(identifier: str) -> None:
        if identifier in visited:
            return
        if identifier in visiting:
            raise OrchestratorBlock(f"work queue dependency cycle at {identifier}")
        visiting.add(identifier)
        for dependency in index[identifier]["dependencies"]:
            visit(dependency)
        visiting.remove(identifier)
        visited.add(identifier)

    for identifier in index:
        visit(identifier)


def load_state() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    delegation = load_json(DELEGATION_PATH, "owner autonomous delegation")
    contract = load_json(CONTRACT_PATH, "autonomous orchestrator contract")
    queue = load_json(QUEUE_PATH, "autonomous work queue")
    promotion = load_json(WORK_UNIT_PROMOTION_PATH, "work-unit promotion contract")
    validate_delegation(delegation)
    validate_contract(contract, delegation)
    validate_promotion_contract(promotion)
    validate_queue(queue, contract)
    return delegation, contract, queue, promotion


def select_work_unit(
    queue: Mapping[str, Any], contract: Mapping[str, Any]
) -> Mapping[str, Any] | None:
    index = {unit["id"]: unit for unit in queue["work_units"]}
    eligible: list[Mapping[str, Any]] = []
    for unit in queue["work_units"]:
        if unit["state"] != "READY":
            continue
        if unit["attempts"] >= unit["max_attempts"]:
            continue
        if not all(index[item]["state"] in TERMINAL_DEPENDENCY_STATES for item in unit["dependencies"]):
            continue
        handler = contract["handlers"][unit["handler"]]
        effect = contract["effect_classes"][unit["effect_class"]]
        if handler.get("automatic") is not True or effect.get("automatic") is not True:
            continue
        eligible.append(unit)
    if not eligible:
        return None
    return min(eligible, key=lambda item: (item["priority"], item["id"]))


def queue_summary(queue: Mapping[str, Any]) -> dict[str, int]:
    result: dict[str, int] = {}
    for unit in queue["work_units"]:
        result[unit["state"]] = result.get(unit["state"], 0) + 1
    return dict(sorted(result.items()))


def observed_head() -> str:
    result = run(("git", "rev-parse", "--verify", "HEAD^{commit}"), timeout=60, check=True)
    return require_sha(result.stdout.strip(), HEX40, "observed HEAD")


def ensure_clean_worktree() -> None:
    result = run(
        ("git", "status", "--porcelain=v1", "--untracked-files=all"),
        timeout=60,
        check=True,
    )
    if result.stdout.strip():
        raise OrchestratorBlock("orchestrator requires a clean worktree")


def branch_slug(identifier: str) -> str:
    value = identifier.lower().replace("aut-", "", 1)
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value[:64] or "work-unit"


def candidate_branch(identifier: str, base_sha: str) -> str:
    require_sha(base_sha, HEX40, "candidate base")
    return f"automation/orchestrator-{branch_slug(identifier)}-{base_sha[:8]}"


def path_allowed(path: str, patterns: Iterable[str]) -> bool:
    normalized = pathlib.PurePosixPath(path).as_posix()
    if normalized.startswith("../") or normalized.startswith("/"):
        return False
    return any(fnmatch.fnmatchcase(normalized, pattern) for pattern in patterns)


def changed_paths(base: str = "HEAD") -> list[str]:
    result = run(("git", "diff", "--name-only", base, "--"), timeout=60, check=True)
    untracked = run(
        ("git", "ls-files", "--others", "--exclude-standard"), timeout=60, check=True
    )
    return sorted(set(result.stdout.splitlines()) | set(untracked.stdout.splitlines()))


def semantic_fingerprint(paths: Sequence[str]) -> str:
    digest = hashlib.sha256()
    for relative in sorted(paths):
        path = ROOT / relative
        if not path.is_file():
            raise OrchestratorBlock(f"fingerprint path is not a file: {relative}")
        payload = path.read_bytes()
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update(hashlib.sha256(payload).digest())
    return digest.hexdigest()


# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
# QIK-VRT autonomous orchestrator source continuation 2/4.
class GitHubClient:
    def __init__(self, repository: str, token: str | None = None) -> None:
        self.repository = repository
        self.token = token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        self.api_root = f"https://api.github.com/repos/{repository}"
        self.timeout = 60

    def _headers(self, *, accept: str = "application/vnd.github+json") -> dict[str, str]:
        headers = {
            "Accept": accept,
            "User-Agent": "qikvrt-autonomous-orchestrator-v2/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: Any | None = None,
        expected: Iterable[int] = (200,),
        accept: str = "application/vnd.github+json",
    ) -> tuple[int, bytes, Mapping[str, str]]:
        if path.startswith("https://"):
            url = path
        else:
            url = self.api_root + (path if path.startswith("/") else f"/{path}")
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            method=method,
            headers=self._headers(accept=accept),
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                status = response.status
                data = response.read()
                headers = dict(response.headers.items())
        except urllib.error.HTTPError as exc:
            status = exc.code
            data = exc.read()
            headers = dict(exc.headers.items()) if exc.headers is not None else {}
        except urllib.error.URLError as exc:
            raise OrchestratorBlock(f"GitHub API transport failed: {exc}") from exc
        if status not in set(expected):
            detail = data.decode("utf-8", errors="replace")[:2000]
            raise OrchestratorBlock(f"GitHub API {method} {path} returned {status}: {detail}")
        return status, data, headers

    def json(
        self,
        method: str,
        path: str,
        *,
        payload: Any | None = None,
        expected: Iterable[int] = (200,),
    ) -> Any:
        _status, data, _headers = self.request(
            method, path, payload=payload, expected=expected
        )
        if not data:
            return None
        try:
            return json.loads(data.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise OrchestratorBlock(f"GitHub API response is not JSON for {path}") from exc

    def paged(self, path: str, *, maximum_pages: int = 10) -> list[Any]:
        separator = "&" if "?" in path else "?"
        result: list[Any] = []
        for page in range(1, maximum_pages + 1):
            data = self.json("GET", f"{path}{separator}per_page=100&page={page}")
            if not isinstance(data, list):
                raise OrchestratorBlock(f"GitHub API paged response is not a list: {path}")
            result.extend(data)
            if len(data) < 100:
                break
        return result

    def download_artifact(self, artifact_id: int, destination: pathlib.Path) -> None:
        if not self.token:
            raise OrchestratorBlock("GitHub token is required for artifact download")
        url = f"{self.api_root}/actions/artifacts/{artifact_id}/zip"
        request = urllib.request.Request(url, method="GET", headers=self._headers())

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
                return None

        opener = urllib.request.build_opener(NoRedirect())
        location: str | None = None
        try:
            with opener.open(request, timeout=self.timeout) as response:
                if response.status == 200:
                    destination.write_bytes(response.read())
                    return
        except urllib.error.HTTPError as exc:
