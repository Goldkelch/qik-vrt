<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# QIK-VRT AI bootstrap

This file is the minimal, tool-neutral entry point for a new human, AI system,
agent, IDE assistant, or automation session.

## Mandatory first action

Before proposing or performing project work:

1. Read `AI_CONTEXT.json`.
2. Read `AGENTS.md`.
3. Read every file listed in `AI_CONTEXT.json` under `required_read_order`.
4. Verify that the repository identity and current Git ref match the context.
5. Treat unresolved contradictions as `EFFECT_ACK_CONTINUE` or
   `EFFECT_ACK_BLOCK`; never guess a project state.

## Canonical-state rule

The repository state is canonical. The two declared QIK-VRT repositories are
**symmetrically canonical** only when the exact relevant bytes and declared
state are verified as equivalent. Neither chat history nor an AI system's
memory overrides repository evidence.

A session is a temporary worker. It reconstructs context from the repository,
performs bounded work, records attributable changes, and hands the resulting
state back through normal review and verification.

## Minimal human handoff

The smallest recommended prompt for any capable system is:

> Read `AI_BOOTSTRAP.md`, load the machine-readable context, verify the current
> repository state, and continue only from the latest verified checkpoint.

For systems able to execute local commands, the equivalent deterministic entry
point is:

```bash
python3 tools/ai_handoff.py
```

The command validates the handoff document with standard-library Python and
prints a compact session brief. It does not modify files, Git state, external
systems, releases, or credentials.

## Licensing boundary

The architecture, protocols, schemas, and interoperability descriptions may be
published as openly available specifications under their explicitly attached
licenses. The concrete implementation, optimizations, runtime machinery,
commercial integrations, and other implementation assets are separate works
and are not automatically granted an open-source license by publication of the
architecture.

No file may be relicensed by inference. The license attached to each file or
repository authority remains controlling. Ambiguity requires rights review.
