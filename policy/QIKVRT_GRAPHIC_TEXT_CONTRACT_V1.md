# QIK-VRT deterministic graphic text contract v1

## Purpose

Generated imagery is probabilistic visual material. It MUST NOT be the authority for exact visible text.

For any graphic containing user-specified wording:

1. The exact wording is stored as UTF-8 source text in the repository.
2. Generative image models MAY generate background, illustration, texture and composition, but MUST NOT be trusted to render authoritative text.
3. Authoritative text MUST be composed deterministically after image generation (SVG/HTML/CSS or another deterministic typesetting stage).
4. The rendered graphic MUST preserve the source text verbatim unless an explicit editorial mutation is separately approved.
5. No additional slogan, paraphrase, signature, translation or explanatory sentence may be introduced into the authoritative text layer unless it is present in the source manifest.
6. Before publication, a machine check MUST compare the text manifest with the deterministic overlay source. A mismatch is fail-closed.
7. Visual inspection remains required for clipping, overlap, contrast and semantic placement. OCR may be used only as supplementary evidence, never as the source of truth.
8. Any mutation creates a successor and resets dependent visual-validation evidence. PREDECESSOR_EVIDENCE_TRANSFER=false.

## Root cause captured

Image generators synthesize glyph-like pixels as part of an image distribution; they do not provide a byte-exact typography guarantee. Prompting for exact spelling is therefore insufficient. QIK-VRT avoids recurrence by separating stochastic imagery from deterministic typography.

## TEMDD acceptance

REQUEST -> bind exact text -> generate non-authoritative visual layer -> deterministic typeset -> compare manifest -> render -> visually reobserve -> ACCEPT.

TRANSPORT_ACK != EFFECT_ACK.
A successful image-generation call is not proof that the requested text was rendered correctly.
