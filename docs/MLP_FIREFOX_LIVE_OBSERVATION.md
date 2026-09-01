# MLP.TOS → Firefox live observation

This stage turns the existing MLP/Firefox integration from a presence check into an actual browser observation.

The proof chain is bound to:

- proven Mega-ST guest TCP/IP head `a71484ba02f6ebe9169af5a291244e99468caec3`;
- exact predecessor tree `b45556a6c4ea2d9946c73264c1ed47d4f3128a76` and unchanged `MLP.TOS` subtree bytes;
- deterministic `MLP.TOS` SHA-256 `5a74c9645d6cdcb2d92770517e31eb7697e180b2ccc4b7fb777c9b558b84ae7e`;
- Firefox-terminal predecessor `e48f50a0419bea9bbdcca47a7673356d372f7400`.

The workflow starts the installed Firefox process in headless mode against a loopback-only proof page. The page executes JavaScript and sends a nonce plus the Firefox user agent back to a loopback HTTP endpoint. Firefox also produces a color PNG screenshot. The receipt binds source head, source tree, MLP digest, TCP/IP predecessor, Firefox version and screenshot digest.

The TCP/IP evidence is a separately bound predecessor tuple, not an ancestry requirement for every downstream candidate. The workflow resolves the Authority remote from `policy/CANONICAL_UPSTREAM_REMOTE_V1.json`, fetches PR #745's exact source ref from that policy-bound remote, verifies its exact commit/tree identity, and compares the current `MLP.TOS` subtree before it starts Firefox. It never treats the checkout's local `origin` name as source authority. This keeps the same content gate executable from both `Goldkelch/qik-vrt` and `ingolf-lohmann/qik-vrt`; a candidate that changes the source subtree holds, while unrelated repository-local branch topology does not falsely fail the observation gate.

This establishes `BROWSER_RENDERING_OBSERVED` and `BROWSER_JAVASCRIPT_OBSERVED` for the exact workflow tuple. It does not establish a protected external effect, extension distribution, owner-authenticated browser authority, `EFFECT_ACK_DONE`, physical original-Mega-ST execution, empirical retrocausal signalling, merge, PASS or FINAL_PASS.

The next proof stage is the controlled Effect-Acknowledgement roundtrip: a separately authorized effect must be prepared, committed, observed and acknowledged, with the acknowledgement returned to the originating Authority context. `REQUESTED != EXECUTED != OBSERVED != ACKNOWLEDGED` remains mandatory throughout.
