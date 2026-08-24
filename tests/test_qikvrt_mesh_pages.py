# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
from __future__ import annotations

import http.server
import json
import pathlib
import tempfile
import threading
import unittest

from tools import qikvrt_mesh_pages as mesh_pages


class QikvrtMeshPagesTests(unittest.TestCase):
    def test_registry_projection_matches_committed_pages(self) -> None:
        mesh_pages.check(mesh_pages.ROOT)
        topology = json.loads((mesh_pages.MESH_ROOT / "topology.json").read_text())
        self.assertEqual(topology["schema"], mesh_pages.TOPOLOGY_SCHEMA)
        self.assertEqual(topology["registry"]["active_count"], 1)
        self.assertEqual(
            topology["nodes"][0]["guid"],
            "a84f157a-cef2-4c47-bca9-8f407085bdbe",
        )
        self.assertEqual(topology["nodes"][0]["repository"], "ingolf-lohmann/qik-vrt")

    def test_client_and_workflows_are_event_driven_without_timers(self) -> None:
        root_html = (mesh_pages.MESH_ROOT / "index.html").read_text()
        for forbidden in ("setInterval(", "setTimeout(", "location.reload("):
            self.assertNotIn(forbidden, root_html)
        self.assertIn("BroadcastChannel", root_html)
        self.assertIn("window.addEventListener('message'", root_html)
        self.assertIn("new EventSource", root_html)

        for relative in (
            ".github/workflows/qikvrt_mesh_pages_delivery.yml",
            ".github/workflows/qikvrt_mesh_pages_main_ledger.yml",
            ".github/workflows/qikvrt_seed_dashboard_publish.yml",
        ):
            workflow = (mesh_pages.ROOT / relative).read_text()
            self.assertNotIn("schedule:", workflow)
            self.assertNotIn("cron:", workflow)

    def test_loopback_system_test_reobserves_every_route_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = pathlib.Path(temporary) / "receipt.json"
            receipt = mesh_pages.local_system_test(mesh_pages.ROOT, output=output)
            self.assertTrue(output.is_file())
            self.assertTrue(receipt["system_test_executed"])
            self.assertTrue(receipt["all_routes_reobserved"])
            self.assertEqual(receipt["network_scope"], "LOOPBACK_HTTP_ONLY")
            self.assertFalse(receipt["github_pages_reachability_observed"])
            self.assertFalse(receipt["browser_rendering_observed"])
            self.assertFalse(receipt["effect_ack_done"])
            self.assertFalse(receipt["pass"])
            self.assertFalse(receipt["final_pass"])

    def test_pages_reobserver_receipt_is_exact_and_fail_closed_on_loopback(self) -> None:
        handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(  # noqa: E731
            *args, directory=str(mesh_pages.DOCS_ROOT), **kwargs
        )
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                output = pathlib.Path(temporary) / "pages.json"
                receipt = mesh_pages.pages_reobserve(
                    root=mesh_pages.ROOT,
                    site_base_url=f"http://127.0.0.1:{server.server_port}/",
                    exact_head="1" * 40,
                    exact_tree="2" * 40,
                    run_id=317,
                    event="system-test",
                    output=output,
                    allow_http_loopback=True,
                )
                self.assertTrue(output.is_file())
                self.assertFalse(receipt["github_pages_reachability_observed"])
                self.assertTrue(receipt["all_active_guid_urls_observed"])
                self.assertTrue(receipt["single_attempt_per_route"])
                self.assertFalse(receipt["periodic_polling"])
                self.assertFalse(receipt["browser_rendering_observed"])
                self.assertFalse(receipt["browser_javascript_observed"])
                self.assertEqual(receipt["external_mutation"], "NONE")
                self.assertFalse(receipt["effect_ack_done"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5.0)

    def test_delivery_and_writer_preserve_authority_boundaries(self) -> None:
        delivery = (
            mesh_pages.ROOT / ".github/workflows/qikvrt_mesh_pages_delivery.yml"
        ).read_text()
        ledger = (
            mesh_pages.ROOT / ".github/workflows/qikvrt_mesh_pages_main_ledger.yml"
        ).read_text()
        self.assertIn("page_build:", delivery)
        self.assertIn("permissions:\n  contents: read", delivery)
        self.assertIn("single", (mesh_pages.MESH_ROOT / "AUDIT.md").read_text().lower())
        self.assertIn("github.event.workflow_run.event == 'page_build'", ledger)
        self.assertIn("actions: read", ledger)
        self.assertIn("contents: write", ledger)
        self.assertIn("AUTHORITY_MAIN_ADVANCED_BEFORE_LEDGER_WRITE", ledger)
        self.assertIn("AUTHORITY_MAIN_ADVANCED_BEFORE_LEDGER_PUSH", ledger)
        self.assertIn("LEDGER_REF_ADVANCED_BEFORE_PUSH", ledger)
        self.assertIn("git -C \"$ledger\" push origin \"HEAD:$LEDGER_REF\"", ledger)


if __name__ == "__main__":
    unittest.main()
