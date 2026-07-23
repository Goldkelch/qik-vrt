# Formalization boundary and completion contract

## Locked source

The formalization is attached to the exact bytes published as Zenodo record
`10.5281/zenodo.21482023`. It does not silently rewrite the manuscript.

- TeX SHA-256: `c55446c62c890e581e9536c0dc8d5de70b7ecf7012a7e2e41744d971da9807cf`
- PDF SHA-256: `b2207d61cd2ff145089d2f1b7cceff8b7f7bd21bce39de7230f553a99a29611f`
- physical PDF pages: 62

Every source span is hashed from raw bytes, with one-based inclusive line
numbers. Physical PDF pages are separately recorded where SyncTeX provides a
deterministic forward mapping. Page metadata is navigational; source bytes and
line-span hashes are the integrity anchors.

## Epistemic dependency order

The claim graph admits the following direction only:

```text
source lock -> definitions -> mathematical/conditional results
mathematical results -> empirical hypotheses -> interpretations
explicit value premises -> normative conclusions
```

An unconditional theorem may not depend, transitively, on an empirical,
interpretive or normative node. A result that needs model/physics assumptions
is `CONDITIONAL`, and those assumptions must occur in its Lean type. Empirical
claims may cite mathematics without inheriting kernel-checked truth about the
world. Interpretive and normative nodes may not carry Lean proof bindings.

Every checked binding also declares its scope. `FULL_ENVIRONMENT` means the
bound proposition discharges the aggregate source claim. `SOURCE_SUBCLAIM`
means the Lean theorem is an exact checked atom extracted from that source
span, while the parent source claim remains `PENDING`. A checked subclaim must
never be counted as completion of its enclosing LaTeX theorem.

## Completion gates

| Gate | Required for full-manuscript status |
|---|---:|
| Definitions typechecked | 20 / 20 |
| Theorem-like environments discharged | 20 / 20 |
| Appendix matrix rows classified | 34 / 34 |
| Remarks inventoried | 5 / 5 |
| Source and span hash failures | 0 |
| Unknown graph edges or cycles | 0 |
| Forbidden proof escapes | 0 |
| Open mathematical proof obligations | 0 |

Until all gates pass, reports must say **partial formalization with explicit
boundaries** and identify the open obligations. Formalizing a definition or a
conditional implication does not establish an empirical correspondence.
