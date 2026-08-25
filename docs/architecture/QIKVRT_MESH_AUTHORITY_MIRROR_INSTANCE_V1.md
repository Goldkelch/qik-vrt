<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# QIK-VRT Mesh Authority/Mirror Instance v1

`QIKVRT_AUTHORITY_MIRROR_MESH_V1` is the mesh-wide control-plane object for
the two designated repositories. It is an observation instance, not a third
repository, a synthetic Git ref, or a synchronization command.

The instance preserves two independent node bindings:

| Node | Repository | Bound fields |
| --- | --- | --- |
| Authority | `Goldkelch/qik-vrt` | `main`, head, root tree, inventory, integrity pair |
| Mirror | `ingolf-lohmann/qik-vrt` | `main`, head, root tree, inventory, integrity pair |

It never writes either node. `mesh_main_ref` is always absent: a pair object is
not a replacement for either node's `main` ref.

## Exact state selection

| State | Predicate | What is not inferred |
| --- | --- | --- |
| `DIVERGED` | Root trees differ | Mesh canonical ref, equality, sync, merge |
| `TREE_EQUALITY_UNVERIFIED_INTEGRITY` | Trees match but integrity evidence is absent or differs | Reciprocal equality receipt, symmetric canonicality |
| `CONTENT_EQUIVALENT_NOT_RECIPROCAL_RECEIPT_BOUND` | Trees and both required integrity hashes match | Reciprocal whole-tree receipt, merge, `PASS`, `FINAL_PASS`, `EFFECT_ACK_DONE` |

The canonical builder is
`tools/qikvrt_authority_mirror_mesh_instance.py`. It accepts an exact input
envelope and derives Executive, Expert, or Full terminal views from the same
canonical bytes. `FULL` carries the complete envelope; shorter views carry its
SHA-256 binding and do not transfer omitted evidence into a claim.

## Inventory boundary

The Mesh inventory is an arithmetic sum only. It can expose the number of
non-main refs (`branches - 1` for each designated node), but it cannot turn
that cardinality into a lifecycle disposition:

```text
NON_MAIN_REF != STALE_REF != ORPHAN_REF != SAFE_TO_DELETE
GC_CANDIDATE != GC_AUTHORIZED
```

The static Live Monitor materializes the same pair shape from public GitHub
GET observations. It states `TREE_EQUALITY_UNVERIFIED_INTEGRITY` when a browser
can observe matching trees but does not possess an exact pair-integrity
binding. It does not synchronize, trigger workflows, submit reviews, merge,
publish, or make any external effect claim.
