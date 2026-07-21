<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# QIK-VRT competition and evaluator entry point

## Thirty-second summary

Most digital systems acknowledge transport, storage, or computation. QIK-VRT
adds a bounded **effect haltpoint** before ordinary downstream release. It
returns exactly one of five states — `NACK`, `CONTINUE`, `DONE`, `ISOLATE`, or
`BLOCK` — and only `DONE` permits ordinary release.

```text
TRANSPORT_ACK != EFFECT_ACK
ordinary_release(result) == (result.state == EFFECT_ACK_DONE)
```

The reference implementation is public, uses Python's standard library for
its active core, and is tied to a fixed release commit, content tree, document
hash, test inventory, and successful GitHub Actions run.

## Evaluator path

1. Run the no-network demonstration:

   ```bash
   python3 examples/effect_haltpoint_demo.py
   ```

2. Run the complete verification gate:

   ```bash
   make test
   ```

3. Inspect the evidence and boundaries:

   - [Submission copy](SUBMISSION.md)
   - [GOAI project introduction — 495 characters](GOAI_PROJECT_INTRO_495_CHARS.txt)
   - [Evidence matrix](EVIDENCE.md)
   - [Two-minute demo script](DEMO_SCRIPT.md)
   - [Eligibility checklist](ELIGIBILITY_CHECKLIST.md)
   - [Prepared GitHub About/topics/social-preview metadata](REPOSITORY_METADATA.md)
   - [GOAI 2026 Agent Infra preparation](GOAI_2026_AGENT_INFRA.md)
   - [Current authority map](../CURRENT_AUTHORITY.md)
   - [Threat model](../QIKVRT_THREAT_MODEL.md)
   - [Social-preview asset](../assets/qikvrt-social-preview.png) and
     [provenance note](../assets/COMPETITION_ASSET_PROVENANCE.md)

## Competition status on 2026-07-21

- No official 2026 edition of GitHub's 2025 **For the Love of Code** challenge
  has been located. The 2025 event is closed; no submission should be made to
  it as though it were open.
- The currently open, technically closest verified event is the
  [GOAI Global Open-source AI Challenge 2026](https://www.goaihz.com/en),
  particularly its
  [Agent Infra track](https://www.goaihz.com/en/tracks?track=infra).
- GOAI preliminary submission requires a project introduction and a PPT/PDF
  proposal deck. Runnable code is optional at that stage. Its later stages
  require an AgentTeams-based multi-agent implementation and runnable demo;
  that extension is planned but is not represented here as already complete.

Registration, acceptance of organizer terms, identity verification, travel
commitments, and final submission must be completed by the author through the
organizer's authenticated account.

## Licensing boundary

The active QIK-VRT-owned code is source-available under PolyForm
Noncommercial 1.0.0, not OSI-approved open source. Documentation and historical
material have separate stated licenses. A competition that requires an
OSI-approved license may therefore be incompatible with the current release.
No competition preparation changes that license boundary.
