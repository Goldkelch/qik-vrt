# QIK-VRT Assimilation / Interoperability Contract

**Status:** normative safety boundary for integration of external cognition, software, services and Internet infrastructure.

## Principle

QIK-VRT MAY assimilate an external component only by making its effects observable, bindable, testable and reversible within an explicitly authorized integration boundary.

Assimilation means **interoperability and evidence-bound composition**, not takeover.

```text
EXTERNAL SYSTEM
  -> OBSERVE
  -> BIND exact subject / interface / authority
  -> ADAPT
  -> SANDBOX
  -> TEST
  -> EXECUTE only authorized effect
  -> OBSERVE
  -> READBACK
  -> ACCEPT
  -> EFFECT_ACK
```

## Mandatory safety invariants

1. **Authority first.** QIK-VRT MUST NOT mutate, control, bypass, exploit, persist into, or expand privileges in a system without explicit authority for that exact effect.
2. **Opt-in boundary.** Internet reachability, public visibility, protocol compatibility, or technical capability MUST NOT be interpreted as authorization.
3. **Least effect.** An adapter MUST request and exercise only the minimum capability required for the declared work unit.
4. **No lateral expansion.** Discovery of another reachable component MUST create an unbound candidate, not authority to act on it.
5. **Fail closed.** Unknown authority, identity, provenance, freshness, or effect state MUST block the corresponding mutation.
6. **Isolation before trust.** Untrusted components MUST be observed and tested through a sandbox or read-only adapter before productive authority is granted.
7. **Effect acknowledgement.** Transport success, API success, process completion, model output, commit, deployment, or test success MUST NOT alone imply the requested effect.
8. **Reversibility.** Where an effect is reversible, its compensation/rollback path SHOULD be bound and tested before productive execution.
9. **Auditability.** Every productive transition MUST bind request, authority, subject, carrier, execution, observation, readback and acceptance evidence.
10. **Human sovereignty.** Integration MUST preserve the legitimate authority and agency of system owners and users; QIK-VRT MUST NOT silently replace them.

## Adapter contract

For external component X and requested effect phi:

```text
ADMISSIBLE(X, phi) iff
  IDENTITY_BOUND(X)
  AND AUTHORITY_BOUND(X, phi)
  AND INTERFACE_BOUND(X)
  AND SUBJECT_CURRENT(X)
  AND POLICY_ALLOWS(phi)
  AND NO_CONTRADICTORY_REQUIRED_EVIDENCE
```

Only then may the TEMDD chain proceed:

```text
COMPILE -> BIND -> RESOLVE -> EXECUTE -> TEST -> OBSERVE -> READBACK -> ACCEPT -> EFFECT_ACK_DONE
```

A failed or unavailable integration does not authorize bypass. It becomes a new evidence/work item inside the authorized boundary.

## Internet-scale composition

The scalable objective is a federation of opt-in adapters:

```text
QIK-VRT Mesh
  <-> authorized repository
  <-> authorized CI/CD
  <-> authorized cloud service
  <-> authorized device
  <-> authorized enterprise system
  <-> authorized cognitive service
```

Each edge carries its own identity, authority, provenance, freshness and effect evidence. There is no implicit global authority.

## Canonical interpretation

```text
ASSIMILATE = make interoperable under explicit authority
           + bind
           + test
           + observe
           + verify effects

ASSIMILATE != seize control
ASSIMILATE != bypass authorization
ASSIMILATE != exploit
ASSIMILATE != global privilege
```

This contract lets QIK-VRT absorb useful capabilities and expose defects through evidence-bound adapters while preserving ownership, authorization and fail-closed control.
