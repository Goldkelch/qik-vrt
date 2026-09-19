# QIK-VRT repository architecture

This is the canonical navigation map for the repository. It describes where
active code, verification, evidence, delivery, publications, and historical
material belong. It does not change protocol semantics or evidence status.

## Thin waist

```text
transport / execution / storage
            |
            v
exact subject + provenance + evidence
            |
            v
five-state Effect-Acknowledgement decision
            |
            v
ordinary effect only at EFFECT_ACK_DONE
```

The normative invariant remains:

```text
TRANSPORT_ACK != EFFECT_ACK
ordinary_release(result) == (result.state == EFFECT_ACK_DONE)
```

Everything outside that waist is an adapter, proof, delivery mechanism,
publication carrier, or historical record.

## Canonical surfaces

| Surface | Canonical locations | Responsibility |
|---|---|---|
| Protocol core | `src/`, `include/` | Five-state semantics and executable core |
| Runtime and adapters | `runtime/`, `tools/`, `scripts/` | Bounded execution, adapters, materializers |
| Delivery | `deploy/`, `dist/`, `release/` | Runtime packaging and delivered artifacts |
| Verification | `tests/`, `formalization/`, `hardware/` | Executable tests and machine-checkable obligations |
| Control plane | `.github/workflows/`, `policy/`, `acceptance/`, `state/` | Admission, review, promotion and fail-closed orchestration |
| Evidence | `evidence/`, `ledger/`, `receipts/`, `audit/` | Append-only observations and receipts |
| Publications | `docs/publications/`, `release/`, `zenodo/` | Publication sources, requests, receipts and readbacks |
| Historical compatibility | `legacy/` | Preserved superseded launchers and compatibility material |

## Front doors

```bash
python3 examples/effect_haltpoint_demo.py
make test
python3 qikvrt.py master-gate
make run-api
```

One-off versioned launchers do not belong at repository root. Historical V45
Windows launchers are preserved byte-for-byte under `legacy/v45/`.

## Dependency direction

```text
protocol core
   ^      ^
   |      |
runtime  verification
   ^      ^
   |      |
delivery  control-plane
   \      /
    evidence
       |
   publication
```

Evidence may describe another layer but must not silently become authority for
that layer. Publication does not imply product acceptance. CI does not imply
review. Transport does not imply effect. A HEAD mutation creates a new exact
subject and requires fresh validation.

## Repository-shape rule

The root is a front door, not an archive. New implementation code belongs in a
canonical surface above. Historical/versioned compatibility material belongs
under `legacy/` or the domain-specific evidence/publication tree.

The machine-readable companion is `policy/REPOSITORY_TOPOLOGY.json`; its
regression test prevents the V45 launcher family from returning to root and
keeps a bounded root-entry budget.
