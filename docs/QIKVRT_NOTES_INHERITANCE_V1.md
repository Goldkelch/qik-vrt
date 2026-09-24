# QIK-VRT Notes inheritance v1

All existing and future QIK-VRT Note/Notes carriers inherit the repository-wide
interpretation that QIK-VRT is an **evidence-bound self-healing repository
architecture**.

Self-healing does not mean that failures disappear automatically. A material
failure becomes a newly bound work subject. A mutation creates a successor
subject. Historical evidence remains auditable, but it does not silently become
authority for the successor.

```text
COMPILE
→ BIND
→ RESOLVE
→ EXECUTE
→ TEST
→ OBSERVE
→ READBACK
→ ACCEPT
→ EFFECT_ACK_DONE
```

The following distinctions remain invariant:

```text
TRANSPORT_ACK ≠ EFFECT_ACK
EXECUTE ≠ DONE
TEST ≠ DONE
OBSERVE ≠ DONE
PREDECESSOR_EVIDENCE_TRANSFER = FALSE
```

An accepted successor may become the next bound input after identity and
provenance have been established.

## Perfect repository as target invariant

```text
every relevant state is identifiable
∧ every mutation creates a distinguishable successor
∧ every claim is evidence-bound
∧ every material failure remains observable
∧ every repair is testable
∧ no intermediate acknowledgement masquerades as terminal completion
∧ accepted successors can become new bound inputs
```

"Perfect" is a target invariant, not a claim that failures are impossible.

## Existing Notes

The exact 11 Note/Release-Note carriers observed on 2026-09-24 are bound in
`state/QIKVRT_NOTES_REGISTRY_V1.json`. Their historical bytes are not rewritten
merely to add this inheritance.

## Future Notes

Every future tracked QIK-VRT file whose basename contains `NOTE` or `NOTES`
(case-insensitive) and whose extension is `.md`, `.txt`, `.tex`, `.json`,
`.yaml`, or `.yml` inherits
`policy/QIKVRT_NOTES_INHERITANCE_V1.json` automatically.

q.e.d.

Ingolf Lohmann
