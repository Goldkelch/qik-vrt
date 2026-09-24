# Generated image text fidelity gate

Status: normative repository quality contract.

## Purpose

Generated images that contain user-supplied text MUST NOT be accepted merely because the composition looks correct. Text rendered inside an image is output data and requires an independent textual readback before acceptance.

## Canonical rule

For every generated image with required literal text:

1. BIND — persist the exact required strings before generation.
2. GENERATE — render the image.
3. OBSERVE — inspect the rendered pixels, not the prompt or intended copy.
4. READBACK — transcribe every visible textual token from the final image.
5. COMPARE — compare required literals byte-for-byte after only explicitly declared Unicode normalization.
6. SPELLCHECK — separately review non-literal prose in each declared language.
7. ACCEPT only when required literals are exact and no visible unintended text remains.
8. Any uncertainty, missing glyph, hallucinated word, duplicated text, spelling error, punctuation drift, or case/underscore mutation is HOLD, never PASS.

PROMPT_TEXT == expected does not imply RENDERED_TEXT == expected.

IMAGE_GENERATED != TEXT_VERIFIED.

## Exact-token protection

Protocol identifiers and signatures are literals. They are not subject to creative rewriting. Examples: Effect_Ack, Effect_Ack_Done, q.e.d., Ingolf Lohmann.

Case, underscores, punctuation, whitespace requirements, and spelling must be validated against the bound source specification.

## Scope fidelity

If the user supplies a closed text set, additional explanatory copy MUST NOT be invented unless explicitly authorized. A visually plausible addition is still a fidelity failure.

## Machine-readable contract

A text-bearing image candidate must have a JSON specification accepted by tools/qikvrt_image_text_gate.py. The validator checks schema integrity, exact required literals, forbidden/unexpected rendered strings supplied by the readback carrier, and fail-closed acceptance state.

This gate does not claim that automated OCR is authoritative. Pixel inspection/readback remains a separate observation. The machine gate validates the bound transcription and comparison record.
