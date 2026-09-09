# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Regression contract for the complete repository workflow_run graph."""

from __future__ import annotations

import pathlib
import unittest

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = ROOT / ".github" / "workflows"


def workflow_documents() -> dict[str, tuple[pathlib.Path, dict[str, object]]]:
    result: dict[str, tuple[pathlib.Path, dict[str, object]]] = {}
    for path in sorted((*WORKFLOW_ROOT.glob("*.yml"), *WORKFLOW_ROOT.glob("*.yaml"))):
        value = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        if not isinstance(value, dict):
            raise AssertionError(f"workflow is not a mapping: {path}")
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
