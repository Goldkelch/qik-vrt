/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */
(() => {
  "use strict";

  const API = "https://api.github.com/repos/Goldkelch/qik-vrt";
  const output = document.getElementById("output");

  async function get(path) {
    const response = await fetch(`${API}${path}`, {
      method: "GET",
      credentials: "omit",
      headers: { Accept: "application/vnd.github+json" },
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  function firstRun(value) {
    return Array.isArray(value.workflow_runs) ? value.workflow_runs[0] || null : null;
  }

  async function observe() {
    const ref = await get("/git/ref/heads/main");
    const head = ref.object.sha;
    const commit = await get(`/git/commits/${head}`);
    const [selfHealValue, watchdogValue, monitorValue] = await Promise.all([
      get("/actions/workflows/qikvrt_autonomous_self_heal.yml/runs?branch=main&event=schedule&per_page=1"),
      get("/actions/workflows/qikvrt_reflexive_repository_watchdog.yml/runs?branch=main&status=completed&per_page=10"),
      get("/actions/workflows/qikvrt_self_heal_terminal_monitor.yml/runs?branch=main&per_page=1"),
    ]);
    const selfHeal = firstRun(selfHealValue);
    const watchdog = (watchdogValue.workflow_runs || []).find((run) => run.head_sha === head && run.conclusion === "success") || null;
    const monitor = firstRun(monitorValue);
    return {
      schema: "qikvrt_firefox_terminal_observation_v1",
      mode: "PASSIVE_MONITOR",
      main: { head, tree: commit.tree.sha },
      self_heal: selfHeal ? {
        run_id: selfHeal.id,
        run_number: selfHeal.run_number,
        status: selfHeal.status,
        conclusion: selfHeal.conclusion,
        head_sha: selfHeal.head_sha,
      } : null,
      reflexive_watchdog: watchdog ? {
        run_id: watchdog.id,
        run_number: watchdog.run_number,
        status: watchdog.status,
        conclusion: watchdog.conclusion,
        head_sha: watchdog.head_sha,
      } : null,
      repository_monitor: monitor ? {
        run_id: monitor.id,
        run_number: monitor.run_number,
        status: monitor.status,
        conclusion: monitor.conclusion,
        head_sha: monitor.head_sha,
      } : null,
      repository_writes: false,
      effect_execution: false,
      note: "Detailed writer/lease and deterministic-blocker classification is preserved in the repository monitor artifact bound to its exact run."
    };
  }

  observe().then((value) => {
    output.textContent = JSON.stringify(value, null, 2);
  }).catch((error) => {
    output.textContent = `CONTINUE\nPublic observation unavailable: ${error.message}\nNo repository or external effect was attempted.`;
  });
})();
