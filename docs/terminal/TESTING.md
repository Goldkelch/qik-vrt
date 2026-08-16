<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# QIK-VRT Repository-Terminal test boundary

The browser terminal is a static, read-only public interface. Its delivery
evidence has three distinct layers; no layer substitutes for another.

## Required test layers

1. `STATIC_SOURCE_AND_SECURITY_CONTRACT` — run
   `python3 -B -m unittest -v tests.test_qikvrt_repository_terminal`.
   It binds the fixed command surface, public GET-only requests,
   `credentials: "omit"`, no credential or repository-write interface,
   accessibility markers, navigation and source notices.
2. `LIVE_PAGE_LOAD` and `DECLARED_CORS_AND_SAME_ORIGIN_READS` — open the
   deployed `/terminal/` page in a browser and exercise `status`, `read AI`,
   `publications`, and `status mirror`. Record the returned repository/ref/head
   and tree, the same-origin publication result, any CORS failure and console
   errors.
3. `FORBIDDEN_INPUT_REJECTION` and `OPT_IN_VOICE_OR_DEVICE_BEHAVIOR` — submit
   a free URL or unlisted command and confirm rejection. Confirm that the
   microphone does not start automatically; if the browser offers recognition,
   a result must remain a visible `ASR_DRAFT` until explicit execution. Record
   browser/device permission denial or unavailability as `CONTINUE` or `BLOCK`.
   Exercise readback start/stop only with non-sensitive output. A visible
   readback state does not prove audible output.

This procedure is bounded to the observed browser, device capability, network,
time and exact repository bytes. It neither transmits credentials nor accepts
them, and it does not make a scientific, security, legal, deployment or general
cross-browser claim.

## Live observation bound to the terminal successor

`QIKVRT_DELIVERY_CLOSURE_BROWSER_E2E_V1` records the 2026-08-16 live observation
against `https://goldkelch.github.io/qik-vrt/terminal/`, which returned
Authority `main` `6f3fa8fe37707e928f840d8a3f2033bec57577b4` and tree
`89d34893793e750a7166de14bf9f1c1c9397dcd2` through the declared public CORS
path. The same session read `/AI`, the same-origin publication index and Mirror
`main` `781cf7a9c1a3457b31004934166e6dacc223c4b9`; it rejected a free URL.

The browser's microphone recognition start produced `not-allowed` and returned
to a safe `CONTINUE` state without automatic execution or stored audio. The
readback controls visibly entered and left their active state. Neither result
proves captured speech recognition nor audible output in another environment.
The detailed metadata-only record is
`state/work_units/QIKVRT_DELIVERY_CLOSURE_BROWSER_E2E_V1.json`.
