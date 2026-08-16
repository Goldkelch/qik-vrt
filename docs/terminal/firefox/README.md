# Firefox reference adapter

This directory is the concrete Firefox WebExtension reference adapter for `QIKVRT_TERMINAL_PATTERN_V1`.

It is intentionally passive. The popup uses fixed public `GET` requests to the Authority repository, omits credentials, accepts no arbitrary URL, requests no repository-write permission, dispatches no workflow, and executes no external effect. It shows current `main`, the latest scheduled autonomous self-heal observation, the latest successful exact-head reflexive watchdog observation, and the repository-native terminal-monitor run.

For the full deterministic classification, writer/lease graph, and first blocker, use the exact monitor run artifact `qikvrt-self-heal-terminal-<run>-<attempt>`. That artifact contains `terminal-snapshot.json` with schema `qikvrt_self_heal_terminal_snapshot_v1`.

## Temporary Firefox loading

For development/review, open `about:debugging`, choose **This Firefox**, select **Load Temporary Add-on**, and select this directory's `manifest.json`. This is a local review action only; it is not a Mozilla Add-ons publication or deployment claim.

Other clients and backends consume the same snapshot schema described by `../TERMINAL_PATTERN_V1.json`. They must preserve exact-head provenance, fail-closed states, and the no-effect boundary.
