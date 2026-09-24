# QIK-VRT External AI Audit Trace v1

This format allows QIK-VRT to audit a tool-using AI execution independently of
the provider that produced it.

## Input boundary

The auditor consumes a **bound execution trace**. It does not claim privileged
access to OpenAI, Anthropic, Google, Meta, xAI, Mistral, or any other provider.
A provider adapter, wrapper, repository workflow, or independent observer must
first materialize the trace.

## Required trace fields

- schema = `qikvrt-external-ai-trace/1.0`
- trace_id
- provider / system / model
- policy_id / policy_version
- subject.id
- authorized_effects
- ordered events
- terminal.state
- terminal.open_obligations

Each event has `seq`, `type`, `subject_id`, and `ok`. EXECUTE events also
name the requested `effect` and may declare `successor_subject_id`.

## Automatic audit

For a claimed `EFFECT_ACK_DONE`, the auditor requires the ordered chain

`BIND → RESOLVE → EXECUTE → TEST → OBSERVE → READBACK → ACCEPT → EFFECT_ACK_DONE`

and additionally verifies:

- the executed effect was explicitly authorized;
- transport receipt was never substituted for effect acknowledgement;
- a successor subject is used after a state-changing execution;
- READBACK is fresh;
- ACCEPT is explicit;
- no open obligation remains.

The result is a machine-readable audit receipt with `PASS` or `BLOCK`.

## Meaning of PASS

PASS means the supplied trace satisfies this audit policy. It does not prove
that hidden provider state matches the trace, that external evidence is true,
that an AI system is generally safe, or that legal/regulatory conformity is
established.

This is the explicit boundary that makes audits of different AI systems
comparable without pretending that brands or model names are themselves
evidence.
