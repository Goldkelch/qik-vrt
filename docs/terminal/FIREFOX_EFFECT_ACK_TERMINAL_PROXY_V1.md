# QIKVRT Firefox EFFECT_ACK Terminal Proxy V1

This document describes the Firefox reference client for the repository-side EFFECT_ACK terminal. It is an implementation profile, not a claim of IETF consensus or standards status.

## Primary delivery requirement

The Product Owner's current priority is a personalized intelligent Firefox behind
the canonical `https://github.com/Goldkelch/qik-vrt/blob/main/AI` entrypoint for
everyone who opens it. Full EFFECT_ACK and the universal terminal contract remain
the acceptance requirements. Extending publications to 47 human languages is
secondary to this usable browser delivery.

Reuse the canonical /AI bridge in PR #893 and the universal-terminal deployment
path in PR #1079. These are integration carriers, not approval or current-head
evidence. The GitHub source page itself cannot launch or install a native browser.
An installed conforming Firefox adapter or a deployed browser session service must
complete the route. For a remote session, each visitor needs a separate profile,
session authorization and storage boundary; a shared owner desktop is insufficient.

The active obligation `AI_PERSONAL_FIREFOX_V1` stays pending until the public route,
the exact deployed Firefox and adapter build, two distinct visitor sessions with
isolation, profile persistence for the same returning visitor, the existing
EFFECT_ACK conformance checks, and authoritative readback are demonstrated. The
deployment must use an appropriately signed or supported managed extension path.
Disabling signature verification in a reference CI profile is not production
delivery. Do not replace missing evidence with a successful HTTP response.

Capability evolution follows `policy/QIKVRT_UNIVERSAL_TERMINAL_DOD_V1.json` and the
existing Mesh adapter contracts. Each newly exposed capability needs its own
exact-subject binding and applicable authority checks. A future capability is not
implicitly implemented or authorized by the interface declaration.

## G20 interface baseline

The initial product interpretation provides at least one suitable interface
language for each of the 19 individual G20 member countries. The EU and African
Union are organizational members; this baseline does not claim coverage of every
official or regional language within them. Country membership source:
[Australian Department of Foreign Affairs and Trade, G20](https://www.dfat.gov.au/trade/organisations/g20).

| Country | Initial interface language(s) |
| --- | --- |
| Argentina | Spanish |
| Australia | English |
| Brazil | Brazilian Portuguese |
| Canada | English, French |
| China | Simplified Chinese |
| France | French |
| Germany | German |
| India | Hindi, English |
| Indonesia | Indonesian |
| Italy | Italian |
| Japan | Japanese |
| Republic of Korea | Korean |
| Mexico | Spanish |
| Russia | Russian |
| Saudi Arabia | Arabic |
| South Africa | English |
| Türkiye | Turkish |
| United Kingdom | English |
| United States | English |

The terminal panel and preference page implement 14 native WebExtension catalogs:
`ar`, `de`, `en`, `es`, `fr`, `hi`, `id`, `it`, `ja`, `ko`, `pt_BR`, `ru`, `tr`,
`zh_CN`. Firefox chooses the catalog using its interface locale and falls back to
English. Arabic uses right-to-left layout; user input has automatic direction.
Catalog content is inserted as text. Protocol states, schema identifiers, request
payloads, tokens and receipt hashes remain canonical. Personal appearance settings
remain in the current Firefox profile and grant no effect authority.

These are machine-generated translation drafts. Catalog coverage and behavioral
tests do not establish independent linguistic review. Firefox's own menus require
the corresponding Mozilla language packs in the delivered browser; translating
the extension does not install those packs. Third-party pages, protocol diagnostics
and other adapter surfaces are outside this initial panel/preferences change.
Localization uses [Mozilla's native WebExtension internationalization](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Internationalization).

## Four-state reference and terminal completion

The persisted D0 decision alphabet is `NOOP`, `HOLD`, `REOBSERVE`,
`REQUEST_AUTHORITY`; its four distinct values require at least two bits. See
`state/work_units/FIXPOINT_D3_8BIT_INFINITY_V1.json` and the linked Lean artifacts.
The D3 fixed projection and the D0 decision value are different objects. The D4
EFFECT_ACK alphabet has five states: `NACK`, `CONTINUE`, `ISOLATE`, `BLOCK`, `DONE`.
The four interaction stages below are a separate UI sequence.

Universal-terminal completion remains bounded by the declared model and exact
subject. New input or a changed subject requires new observation. Neither this
interface implementation nor this citation is a new Lean kernel run or a proof of
completed public browser delivery.

## Boundary

The browser terminal separates four states that must remain visually and mechanically distinct:

1. **Local observation** — repository state, camera preview, microphone recording and personalization can exist locally without being submitted.
2. **Submitted input / Prepare** — explicitly selected text or media is serialized and sent to the configured EFFECT_ACK backend in `prepare` mode. Prepare must not execute the protected effect.
3. **Prepared DONE** — the client has received a compact `Effect-Ack` assertion and the corresponding exact record/token binding required by the deployment profile. This still is not the protected effect.
4. **Commit and reobservation** — only a valid DONE preparation enables Commit. After Commit, the terminal reobserves the authoritative state and treats the post-effect observation as new evidence.

`HTTP success != EFFECT_ACK_DONE != independently observed external effect`.

## Firefox reference extension

The implementation lives under `browser/firefox/qikvrt-terminal/` and uses a Manifest V3 event-page background script. The content script is injected only into the configured QIKVRT Authority AI page and GitHub Pages surface. The background script has the narrow host permissions required for public Authority observation and the loopback reference backend.

The extension provides:

- source-bound `main` head/tree observation;
- a five-minute repository watchdog stored in local extension state;
- latest Self-Heal, reflexive Watchdog and terminal-monitor workflow observations;
- text interaction;
- explicit microphone recording via a user gesture;
- explicit camera preview and still-image snapshot via a user gesture;
- local-only media state until Prepare;
- Prepare / DONE-gated Commit;
- post-commit repository reobservation;
- local personalization for accent, font scale, density and position.

## Proxy model

Firefox is the reference renderer and proxy, not a privileged truth source. Other clients and backends map their observations to `qikvrt_terminal_frame_v1` while retaining provenance.

Supported adapter classes are:

- public GitHub repository observation;
- HTTP backend;
- loopback QIKVRT bridge;
- MCP/agent observation;
- another client snapshot with an explicit source identifier.

A proxy may display NACK, CONTINUE, ISOLATE or BLOCK. It may never translate those states into ordinary release. Rendering a DONE record does not itself execute an effect.

## Repository-side reference bridge

`src/qikvrt_effect_ack_http_terminal.py` is loopback-only and deliberately has `external_effect = NONE`. It demonstrates capability discovery, bounded Prepare, a short-lived single-use exact-bound token, Commit, replay refusal and post-effect observation of a local terminal event.

It is not a replacement for `src/qikvrt_effect_ack.py`, and it must not be represented as proof of complete wire or deployment conformance. A write-capable repository, publication, deployment or actuator backend needs a separately authorized adapter and must preserve the same EFFECT_ACK gate.

## HTTP / HTML integration

The companion Internet-Draft candidate is `external/ietf/draft-lohmann-qikvrt-effect-ack-http-00.xml`. It defines:

- `Effect-Ack-Request` as a Structured Dictionary;
- `Effect-Ack` as a Structured Dictionary;
- `effect-ack` as a Web Linking relation;
- two-phase Prepare / Commit;
- the same relation in an ordinary HTML `link` element without a new HTML element or parser feature.

Legacy HTTP/HTML remains unchanged. A fail-closed client that requires EFFECT_ACK protection must discover support before sending the protected operation.

## Security and privacy

- Device acquisition requires explicit browser permission and a user gesture.
- Media remains local until explicit Prepare.
- Personalization remains local by default.
- The reference backend is loopback-only.
- Commit tokens are single-use and time-bounded.
- Old exact-head evidence is never transferred to a new head.
- A browser permission is not effect authorization.
- No PASS, FINAL_PASS or EFFECT_ACK_DONE claim follows merely from installing the extension or passing repository tests.
