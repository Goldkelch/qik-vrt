# QIK-VRT Epistemic Spiral terminal surface

This directory materializes the Product Owner's epistemic-spiral concept as a
web-native, vector animation suitable for the QIK-VRT Pages surface, the
Universal Terminal, Firefox and the Linux distribution.

## Meaning

The core invariant is:

`observed + accepted successor -> next bound input`

The Product Owner interprets this as a **universal creation principle** spanning
learning, computation, life and cosmos. QIK-VRT preserves that claim while
keeping evidence classes separate:

- owner-asserted cross-domain interpretation: present;
- scoped formal components: present elsewhere in the repository;
- independent empirical confirmation that the whole physical universe operates
  exactly by this principle: **not established**.

The animation is therefore explanatory and hypothesis-bearing. Rendering it is
not a physical proof and not an Effect-Acknowledgement.

## Localization

The surface implements the same 14 baseline locales as the Firefox terminal:
`ar de en es fr hi id it ja ko pt_BR ru tr zh_CN`.

Translations are machine-generated drafts pending independent linguistic
review, matching the existing browser localization boundary.

## Carriers

- public Pages candidate: `/terminal/epistemic-spiral/`;
- Universal Terminal runtime: `/AI/spiral/`;
- canonical AI bootstrap: root `/AI` links to the public/runtime surfaces;
- Linux Mega-ST distribution: copied into
  `/opt/qikvrt/share/epistemic-spiral/` with a desktop launcher;
- Cloud Transputer OCI carrier: repository bytes are included under
  `/opt/qikvrt/docs/terminal/epistemic-spiral/`.

## Verification

`tools/qikvrt_epistemic_spiral_roundtrip.py` canonicalizes the state and locale
objects, serializes them to JSON bytes, transports them through Base64 wire
representation, deserializes and verifies byte identity. The Cloud Transputer
workflow re-runs this receipt **inside the built image**. The Mega-ST workflow
verifies the materialized files inside the generated squashfs.

These checks prove the declared digital carrier path only. They do not prove a
public deployment, physical MC68000 execution, a law of nature or
`EFFECT_ACK_DONE`.
