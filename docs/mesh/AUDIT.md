# QIK-VRT Mesh Pages audit

Copyright 2026 Ingolf Lohmann. SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0.

## Verified delivery chain

The delivery unit binds these stages without collapsing them:

```text
registry source
-> deterministic /mesh/ topology and GUID pages
-> exact-head verification
-> loopback HTTP system test
-> Authority-main integration
-> GitHub Pages page_build event
-> single HTTPS observation per required route
-> fail-closed receipt
-> serialized receipt ledger
```

The projection contains only registry entries whose registry, policy, and effective states are `ACCEPTED`, `ACTIVE`, and `ACTIVE`.

## Event model

This unit has no `schedule:` trigger, periodic timer, retry loop, or time-driven semantic continuation. Pull-request changes, Authority-main pushes, `page_build`, and completion of the named verifier are the productive events. A failed route observation stays failed; a later event may create a separately bound run.

## Trust boundary

Candidate verification is read-only. Ledger persistence is a separate main-only stage. It verifies the exact source run and receipt, revalidates live Authority `main`, serializes concurrent ledger attempts, compares the ledger head, and permits only a normal fast-forward update.

The main checks are revalidation points, not an atomic transaction across the main and ledger refs. The receipt claims equality only at the explicit checks.

## Fail-closed receipt

A successful productive receipt may set these scoped observations:

```text
GITHUB_PAGES_REACHABILITY_OBSERVED=true
AUTHORITY_MESH_ROOT_OBSERVED=true
MACHINE_TOPOLOGY_OBSERVED=true
ALL_ACTIVE_GUID_URLS_OBSERVED=true
SINGLE_ATTEMPT_PER_ROUTE=true
PERIODIC_POLLING=false
```

It keeps browser rendering, browser JavaScript, general Internet reachability, repository synchronization, physical execution, independent review, `PASS`, `FINAL_PASS`, and general `EFFECT_ACK_DONE` unclaimed.

`SOURCE_PRESENT_ON_PR != EFFECTIVE_ON_MAIN != PAGES_DEPLOYED != PAGES_REOBSERVED != BROWSER_REOBSERVED != EFFECT_ACK_DONE`.
