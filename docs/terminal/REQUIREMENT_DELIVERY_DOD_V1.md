# QIK-VRT Requirement Delivery Definition of Done v1

**Product Owner:** Ingolf Lohmann

A Pull Request, successful check, review, merge, upload or HTTP response is not a
completed requirement.

The repository-wide completion condition is:

```text
REQUIREMENT
  -> canonical deliverable on Trusted Main
  -> fresh observation of that exact Main head
  -> derive every applicable delivery obligation
  -> execute each machine-owned delivery edge
  -> authoritative external readback
  -> EFFECT_ACK_DONE for every obligation
  -> DONE
```

The machine-readable contract is
`policy/QIKVRT_REQUIREMENT_DELIVERY_DOD_V1.json`.  Current obligations live in
`state/delivery/ACTIVE_DELIVERY_OBLIGATIONS_V1.json`; each external operation has
an exact request under `state/delivery/requests/`.

## Fail-closed states

`WAIT_MAIN` means the canonical deliverable is not yet present on Trusted Main.
No predecessor PR evidence can satisfy it.

`WAIT_EXACT_MAIN_REOBSERVATION` means the file is on Main but the resulting exact
Main head has not yet received the required fresh observation.

`DELIVERY_REQUIRED` means Main and its observation are bound, but the external
Effect-ACK is absent, stale, bound to another Main head, or lacks authoritative
readback.

`DONE` is reachable only when all three layers are exact and complete.

## Current application

The first active ledger applies the invariant immediately to:

1. `docs/LEAN_LAKE_PROOF_STATUS.md` -> transparent Wikipedia COI/edit request;
2. Planck-Tick Gap Law manuscript -> Zenodo record with DOI/file-hash readback;
3. Planck-Tick Gap Law manuscript -> authenticated arXiv submission with
   submission-ID/status readback.

The Wikipedia operation is intentionally a transparent COI path.  It may add
only facts supported by the current proof/status provenance and suitable
independent sources.  It must not present a physical hypothesis as established
physics, a primary-source publication as independent notability, or QIK-VRT's
operational Zero-Bug invariant as proof that unknown defects cannot exist.

## Universal terminal adapter

`policy/QIKVRT_EFFECT_ACK_HTTP_TERMINAL_V1.json` now authorizes bound delivery
requests for Zenodo, arXiv, Wikipedia, IETF, IEEE and generic authenticated web
operations.  Authorization does not weaken EFFECT_ACK: prepare does not execute
the protected effect; commit is exact-bound and single-use; HTTP success alone
cannot establish effect; authoritative post-effect readback is mandatory.

A platform edge that lacks a configured executable adapter remains unfinished.
It must stay `DELIVERY_REQUIRED` or `REQUEST_AUTHORITY`; it may never be rounded
up to DONE.  Independent machine-owned delivery obligations continue.
