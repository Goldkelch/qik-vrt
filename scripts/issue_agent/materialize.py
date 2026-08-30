#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

MAX_FILES = 40
MAX_BYTES = 180_000
PATTERNS = ("README*.md", "docs/**/*.md", "formalization/**/*.md", "formalization/**/*.lean", "spec/**/*.md")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--issue", required=True)
    p.add_argument("--repository", required=True)
    p.add_argument("--output-dir", required=True)
    args = p.parse_args()

    issue = json.loads(Path(args.issue).read_text(encoding="utf-8"))
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # ``updated_at`` advances for repository-generated comments and refreshes.
    # It is observation metadata, not a causal change to the issue request, so
    # it must not enter REQUEST.sha256 or create another continuation.
    request = {
        "repository": args.repository,
        "issue_number": issue["number"],
        "title": issue.get("title", ""),
        "body": issue.get("body") or "",
        "author": (issue.get("user") or {}).get("login"),
        "html_url": issue.get("html_url"),
        "created_at": issue.get("created_at"),
    }
    canonical = json.dumps(request, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    (out / "REQUEST.json").write_text(canonical, encoding="utf-8")
    (out / "REQUEST.sha256").write_text(hashlib.sha256(canonical.encode()).hexdigest() + "  REQUEST.json\n", encoding="utf-8")
    # Do not persist a second observation artifact containing ``updated_at``:
    # a later broad staging command must not be able to turn it into a fresh
    # branch update.  The exact semantic request and source binding are the
    # durable evidence product.

    seen = set()
    selected = []
    total = 0
    for pattern in PATTERNS:
        for path in sorted(Path(".").glob(pattern)):
            if not path.is_file() or ".git" in path.parts or path in seen:
                continue
            data = path.read_bytes()
            if len(selected) >= MAX_FILES or total + len(data) > MAX_BYTES:
                continue
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                continue
            selected.append((path.as_posix(), text))
            seen.add(path)
            total += len(data)

    lines = [
        "# Repository context for issue processing",
        "",
        "This context is deterministic, size-bounded, and derived from the checked-out repository.",
        "It is evidence input, not an assertion that every included file is relevant.",
        "",
    ]
    for name, text in selected:
        lines.extend([f"## `{name}`", "", text, ""])
    (out / "CONTEXT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
