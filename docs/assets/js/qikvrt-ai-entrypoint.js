/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */

(function () {
  "use strict";

  function initialize() {
    const route = new URL("../terminal/?qikvrt_ai_entry=1", window.location.href);
    const link = document.getElementById("terminalRoute");
    const status = document.getElementById("aiRouteStatus");

    if (!link || !status || route.origin !== window.location.origin) {
      throw new Error("canonical same-origin terminal route unavailable");
    }

    link.href = route.href;
    status.textContent = "AI_ROUTE_READY";
    document.documentElement.dataset.qikvrtAiRoute = "ready";

    window.QIKVRTAIEntrypoint = Object.freeze({
      schema: "qikvrt_canonical_ai_route_v1",
      ready: true,
      route: route.href,
      sameOrigin: true,
      effectAck: "NOT_PERFORMED",
      externalEffect: "NONE"
    });

    const parameters = new URL(window.location.href).searchParams;
    if (parameters.get("navigate") === "terminal") {
      window.requestAnimationFrame(function () {
        window.location.assign(route.href);
      });
    }
  }

  document.addEventListener("DOMContentLoaded", initialize);
})();
