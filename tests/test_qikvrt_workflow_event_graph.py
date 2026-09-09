# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Regression contract for the complete repository workflow_run graph."""

from __future__ import annotations

import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = ROOT / ".github" / "workflows"


def scalar(value: str) -> str:
    """Read the small, string-only YAML subset used by workflow triggers.

    This graph contract deliberately has no PyYAML dependency: the GitHub
    runners that execute the watchdog contracts provide Python, but do not
    promise a third-party YAML package.  It accepts only the trigger fields
    below and fails closed for malformed values rather than pretending to be a
    general YAML parser.
    """

    value = value.strip()
    if " #" in value:
        value = value.split(" #", 1)[0].rstrip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    if not value:
        raise AssertionError("workflow scalar is empty")
    return value


def indentation(line: str) -> int:
    if "\t" in line[: len(line) - len(line.lstrip())]:
        raise AssertionError("workflow YAML may not use tabs for indentation")
    return len(line) - len(line.lstrip(" "))


def block_end(lines: list[str], start: int, indent: int) -> int:
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if not stripped or stripped.startswith("#"):
            continue
        if indentation(lines[index]) <= indent:
            return index
    return len(lines)


def key_index(lines: list[str], start: int, end: int, key: str, indent: int) -> int | None:
    prefix = re.compile(
        rf"^{' ' * indent}(?:{re.escape(key)}|['\"]{re.escape(key)}['\"]):"
    )
    for index in range(start, end):
        line = lines[index]
        if indentation(line) == indent and prefix.match(line):
            return index
    return None


def inline_or_block_list(lines: list[str], index: int, end: int, key: str, indent: int) -> list[str]:
    raw = lines[index][len(" " * indent + key + ":") :].strip()
    if raw:
        if not (raw.startswith("[") and raw.endswith("]")):
            raise AssertionError(f"{key} must use a YAML list")
        values = [scalar(part) for part in raw[1:-1].split(",") if part.strip()]
        if not values:
            raise AssertionError(f"{key} list is empty")
        return values

    values: list[str] = []
    item_prefix = " " * (indent + 2) + "-"
    for candidate in range(index + 1, end):
        line = lines[candidate]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        candidate_indent = indentation(line)
        if candidate_indent <= indent:
            break
        if candidate_indent != indent + 2 or not line.startswith(item_prefix):
            raise AssertionError(f"{key} contains a non-list value")
        values.append(scalar(line[len(item_prefix) :]))
    if not values:
        raise AssertionError(f"{key} list is empty")
    return values


def workflow_document(path: pathlib.Path) -> dict[str, object]:
    lines = path.read_text(encoding="utf-8").splitlines()
    name_match = next(
        (
            re.match(r"^name:\s*(.+?)\s*$", line)
            for line in lines
            if indentation(line) == 0 and line.startswith("name:")
        ),
        None,
    )
    if name_match is None:
        raise AssertionError(f"workflow has no name: {path}")
    name = scalar(name_match.group(1))

    on_index = key_index(lines, 0, len(lines), "on", 0)
    if on_index is None:
        raise AssertionError(f"workflow has no on trigger: {path}")
    on_end = block_end(lines, on_index, 0)
    triggers: dict[str, object] = {}

    workflow_run_index = key_index(lines, on_index + 1, on_end, "workflow_run", 2)
    if workflow_run_index is not None:
        workflow_run_end = block_end(lines, workflow_run_index, 2)
        values: dict[str, object] = {}
        for key in ("workflows", "types"):
            value_index = key_index(lines, workflow_run_index + 1, workflow_run_end, key, 4)
            if value_index is not None:
                values[key] = inline_or_block_list(lines, value_index, workflow_run_end, key, 4)
        triggers["workflow_run"] = values

    schedule_index = key_index(lines, on_index + 1, on_end, "schedule", 2)
    if schedule_index is not None:
        schedule_end = block_end(lines, schedule_index, 2)
        schedules: list[dict[str, str]] = []
        for candidate in range(schedule_index + 1, schedule_end):
            line = lines[candidate]
            match = re.match(r"^    -\s+cron:\s*(.+?)\s*$", line)
            if match:
                schedules.append({"cron": scalar(match.group(1))})
        if not schedules:
            raise AssertionError(f"schedule has no cron expression: {path}")
        triggers["schedule"] = schedules

    if key_index(lines, on_index + 1, on_end, "workflow_dispatch", 2) is not None:
        triggers["workflow_dispatch"] = {}

    return {"name": name, "on": triggers}


def workflow_documents() -> dict[str, tuple[pathlib.Path, dict[str, object]]]:
    result: dict[str, tuple[pathlib.Path, dict[str, object]]] = {}
    for path in sorted((*WORKFLOW_ROOT.glob("*.yml"), *WORKFLOW_ROOT.glob("*.yaml"))):
        value = workflow_document(path)
        name = value.get("name")
        if not isinstance(name, str) or not name:
            raise AssertionError(f"workflow has no name: {path}")
        if name in result:
            raise AssertionError(f"duplicate workflow name {name!r}: {path} and {result[name][0]}")
        result[name] = (path, value)
    return result


def workflow_run_spec(document: dict[str, object]) -> tuple[list[str], list[str]]:
    triggers = document.get("on", {})
    if not isinstance(triggers, dict):
        raise AssertionError("workflow on trigger is not a mapping")
    workflow_run = triggers.get("workflow_run")
    if workflow_run is None:
        return [], []
    if not isinstance(workflow_run, dict):
        raise AssertionError("workflow_run trigger is not a mapping")
    targets = workflow_run.get("workflows", [])
    types = workflow_run.get("types", [])
    if isinstance(targets, str):
        targets = [targets]
    if isinstance(types, str):
        types = [types]
    if not isinstance(targets, list) or not all(isinstance(item, str) and item for item in targets):
        raise AssertionError("workflow_run workflows must be a list of non-empty names")
    if not isinstance(types, list) or not all(isinstance(item, str) and item for item in types):
        raise AssertionError("workflow_run types must be a list of non-empty names")
    return list(targets), list(types)


class WorkflowEventGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sources = workflow_documents()
        cls.targets = {
            name: workflow_run_spec(document)[0]
            for name, (_path, document) in cls.sources.items()
        }
        cls.types = {
            name: workflow_run_spec(document)[1]
            for name, (_path, document) in cls.sources.items()
        }
        cls.graph = {
            name: list(targets)
            for name, targets in cls.targets.items()
        }

    def test_every_workflow_run_target_resolves_to_one_repository_workflow(self) -> None:
        unknown = [
            f"{name} -> {target}"
            for name, targets in self.targets.items()
            for target in targets
            if target not in self.sources
        ]
        self.assertEqual(unknown, [])

    def test_workflow_run_dependency_graph_is_acyclic(self) -> None:
        visiting: list[str] = []
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visiting:
                cycle = visiting[visiting.index(name) :] + [name]
                self.fail("workflow_run cycle: " + " -> ".join(cycle))
            if name in visited:
                return
            visiting.append(name)
            for target in self.graph[name]:
                visit(target)
            visiting.pop()
            visited.add(name)

        for name in sorted(self.graph):
            visit(name)

    def test_workflow_run_depth_is_at_most_three(self) -> None:
        """GitHub starts A -> B -> C -> D, but silently drops a fifth run."""
        consumers = {name: [] for name in self.sources}
        for consumer, upstreams in self.targets.items():
            for upstream in upstreams:
                consumers[upstream].append(consumer)

        longest: list[str] = []

        def visit(name: str, path: list[str]) -> None:
            nonlocal longest
            if len(path) > len(longest):
                longest = path
            for consumer in consumers[name]:
                if consumer in path:
                    self.fail("workflow_run cycle: " + " -> ".join(path + [consumer]))
                visit(consumer, path + [consumer])

        for name in sorted(consumers):
            visit(name, [name])
        self.assertLessEqual(
            len(longest) - 1,
            3,
            "workflow_run depth exceeds GitHub's three-edge limit: " + " -> ".join(longest),
        )

    def test_watchdog_does_not_extend_the_promotion_chain_to_a_fourth_edge(self) -> None:
        """The terminal promotion run must not trigger another workflow_run observer."""
        ci = "QIKVRT CI"
        review_executor = "QIKVRT requested review executor"
        required_review = "QIKVRT required code-owner review"
        promotion = "QIK-VRT expected-head promotion executor"
        watchdog = "QIKVRT reflexive repository watchdog"

        # This is the platform-limited productive chain.  Adding `promotion`
        # to the watchdog's upstream targets would create a fourth edge and
        # GitHub would silently drop the watchdog execution.
        self.assertIn(ci, self.targets[review_executor])
        self.assertIn(review_executor, self.targets[required_review])
        self.assertIn(required_review, self.targets[promotion])
        self.assertNotIn(promotion, self.targets[watchdog])

    def test_bot_issue_comment_projection_cannot_reenter_requested_review(self) -> None:
        """A live-status comment must not close a review-executor feedback loop."""
        review_executor = "QIKVRT requested review executor"
        live_status = "QIKVRT live status watch"
        executor_path, _executor = self.sources[review_executor]
        live_status_path, _live_status = self.sources[live_status]
        executor = executor_path.read_text(encoding="utf-8")
        live_status_text = live_status_path.read_text(encoding="utf-8")

        # The productive workflow_run edge is intentional. The live observer
        # then writes its durable PR issue-comment projection, so the review
        # executor must stop that bot-authored callback at its job ingress.
        self.assertIn(review_executor, self.targets[live_status])
        self.assertIn("issue_comment:", executor)
        self.assertIn("issues/$pr/comments", live_status_text)
        self.assertIn(
            "github.event_name == 'issue_comment'",
            executor,
        )
        self.assertIn(
            "github.event.comment.user.login == 'github-actions[bot]'",
            executor,
        )

    def test_platform_monitor_is_the_only_scheduled_workflow(self) -> None:
        scheduled = [
            (path.name, (document.get("on") or {}).get("schedule"))
            for _name, (path, document) in self.sources.items()
            if (document.get("on") or {}).get("schedule") is not None
        ]
        self.assertEqual(
            scheduled,
            [("qikvrt_reflexive_repository_watchdog.yml", [{"cron": "*/5 * * * *"}])],
        )

    def test_observer_pair_only_admits_completed_productive_events(self) -> None:
        watchdog = "QIKVRT reflexive repository watchdog"
        status = "QIKVRT live status watch"
        watchdog_path, _watchdog = self.sources[watchdog]
        status_path, _status = self.sources[status]
        self.assertEqual(watchdog_path.name, "qikvrt_reflexive_repository_watchdog.yml")
        self.assertEqual(status_path.name, "qikvrt_live_status_watch.yml")
        self.assertEqual(self.types[watchdog], ["completed"])
        self.assertEqual(self.types[status], ["completed"])
        self.assertNotIn(status, self.targets[watchdog])
        self.assertNotIn(watchdog, self.targets[status])


if __name__ == "__main__":
    unittest.main()
