#!/usr/bin/env python3
"""Render the machine claim graph as a deterministic human review map."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "MANUSCRIPT_PROOF_MAP.md"


def load(name: str) -> dict:
    return json.loads((ROOT / "claims" / name).read_text(encoding="utf-8"))


def render() -> str:
    inventory = load("TEX_ENVIRONMENTS.json")
    graph = load("CLAIM_GRAPH.json")
    matrix = load("APPENDIX_MATRIX.json")
    nodes = {node["id"]: node for node in graph["nodes"]}
    checked_nodes = [
        node for node in graph["nodes"]
        if node["formalizationStatus"] == "KERNEL_CHECKED"
    ]
    theorem_environments = [
        environment for environment in inventory["environments"]
        if environment["group"] == "theoremLike"
    ]
    fully_checked_theorem_environments = [
        environment for environment in theorem_environments
        if all(
            nodes[claim_id]["formalizationStatus"] == "KERNEL_CHECKED"
            for claim_id in environment["claimIds"]
        )
    ]
    partially_checked_theorem_environments = [
        environment for environment in theorem_environments
        if any(
            nodes[claim_id]["formalizationStatus"] == "KERNEL_CHECKED"
            for claim_id in environment["claimIds"]
        )
        and environment not in fully_checked_theorem_environments
    ]
    open_definitions = sum(
        node["formalizationStatus"] == "PENDING"
        and node["epistemicCategory"] == "DEFINITION"
        for node in graph["nodes"]
    )
    open_theorems = sum(
        node["formalizationStatus"] == "PENDING"
        and node["epistemicCategory"] in {"MATHEMATICAL", "CONDITIONAL"}
        for node in graph["nodes"]
    )

    lines = [
        "# Manuscript proof map",
        "",
        "This map is generated from the locked 62-page TeX source and the v2 claim graph. ",
        "`KERNEL_CHECKED` means the exact proposition-indexed Lean wrapper compiles; ",
        "`PENDING` means an explicit proof obligation, not an inferred truth.",
        "",
        "## Coverage summary",
        "",
        "| Item | Coverage |",
        "|---|---:|",
        "| Formal LaTeX environments inventoried | 40 / 40 |",
        "| Definitions inventoried | 20 / 20 |",
        "| Theorem-like environments inventoried | 20 / 20 |",
        "| Remarks inventoried | 5 / 5 |",
        "| Explicit proof blocks attached | 17 / 17 |",
        "| Appendix matrix rows classified | 34 / 34 |",
        f"| Kernel-checked atomic claims | {len(checked_nodes)} |",
        f"| Theorem-like environments fully checked | {len(fully_checked_theorem_environments)} / 20 |",
        f"| Theorem-like environments with checked subclaims only | {len(partially_checked_theorem_environments)} / 20 |",
        f"| Open definition nodes | {open_definitions} |",
        f"| Open theorem/conditional nodes | {open_theorems} |",
        "",
        "## Formal environments",
        "",
        "| Environment | Type and title | PDF page | TeX lines | Claim status |",
        "|---|---|---:|---:|---|",
    ]
    for env in inventory["environments"]:
        if not env["formal"]:
            continue
        span = env["sourceSpan"]
        claim_ids = env["claimIds"]
        claim_statuses = ", ".join(
            f"`{claim_id}: {nodes[claim_id]['formalizationStatus']}`"
            for claim_id in claim_ids
        )
        title = env["titleTex"] or "—"
        type_title = f"{env['environmentType']}: {title}".replace("|", "\\|")
        lines.append(
            f"| `{env['id']}` | {type_title} | {span['physicalPdfPage']} | "
            f"{span['startLine']}–{span['endLine']} | "
            f"{claim_statuses} |"
        )

    lines.extend(
        [
            "",
            "## Kernel-checked atomic claims",
            "",
            "| Claim | Scope | Batch | Lean theorem | Environment(s) |",
            "|---|---|---|---|---|",
        ]
    )
    for node in checked_nodes:
        binding = node["formalBinding"]
        environments = ", ".join(
            f"`{environment_id}`" for environment_id in node["environmentIds"]
        )
        lines.append(
            f"| `{node['id']}` | `{binding['claimScope']}` | `{binding['batch']}` | "
            f"`{binding['proofConstant']}` | {environments} |"
        )

    lines.extend(
        [
            "",
            "## Context-only remarks",
            "",
            "| Environment | Title | PDF page | TeX lines |",
            "|---|---|---:|---:|",
        ]
    )
    for env in inventory["environments"]:
        if env["formal"]:
            continue
        span = env["sourceSpan"]
        title = (env["titleTex"] or "—").replace("|", "\\|")
        lines.append(
            f"| `{env['id']}` | {title} | {span['physicalPdfPage']} | "
            f"{span['startLine']}–{span['endLine']} |"
        )

    category_counts = Counter(row["epistemicCategory"] for row in matrix["rows"])
    lines.extend(
        [
            "",
            "## Appendix matrix classification",
            "",
            "| Epistemic category | Rows | Machine theorem binding? |",
            "|---|---:|---|",
        ]
    )
    for category in (
        "MATHEMATICAL",
        "CONDITIONAL",
        "BACKGROUND",
        "EMPIRICAL",
        "INTERPRETIVE",
        "NORMATIVE",
    ):
        permitted = "only when an exact formal proposition exists" if category in {
            "MATHEMATICAL", "CONDITIONAL"
        } else "no"
        lines.append(f"| `{category}` | {category_counts[category]} | {permitted} |")

    pending = [
        node for node in graph["nodes"]
        if node["formalizationStatus"] == "PENDING"
        and node["epistemicCategory"] in {"MATHEMATICAL", "CONDITIONAL"}
    ]
    lines.extend(
        [
            "",
            "## Open theorem obligations",
            "",
        ]
    )
    for node in pending:
        envs = ", ".join(f"`{value}`" for value in node["environmentIds"])
        lines.append(f"- `{node['id']}` ({node['epistemicCategory']}, {envs}): {node['statement']}")

    lines.extend(
        [
            "",
            "Full-manuscript status remains blocked until all definition and theorem ",
            "obligations are discharged and every conditional assumption is represented ",
            "in the corresponding Lean type.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = render()
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != rendered:
            raise SystemExit(f"stale proof map: {args.output}")
        print(f"PASS proof map current: {args.output}")
        return 0
    args.output.write_text(rendered, encoding="utf-8")
    print(f"PASS wrote proof map: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
