# QIK-VRT LIVE STATUS — MLP.PRG -> Firefox terminal

This file exists so the current implementation/proof state is visible directly in the repository tree and in PR #746 Files changed.

## Current implementation state

- PR: #746
- MLP source lineage: #744 -> #745 -> #746
- `MLP.TOS` source SHA-256: `5a74c9645d6cdcb2d92770517e31eb7697e180b2ccc4b7fb777c9b558b84ae7e`
- guest-visible launch filename: `C:\MLP.PRG`
- terminal mode: interactive terminal, not monitor-only
- Firefox runtime strategy: stock Firefox/Gecko + QIK-VRT WebExtension terminal
- Effect-Ack stages wired: discovery, prepare, bound record validation, commit, post-effect boundary

## What has actually succeeded

On the semantic candidate, the dedicated `QIKVRT MLP Firefox terminal` workflow completed successfully. The repository integrity materializer then advanced the branch to a bot-authored materialization head, which requires fresh exact-head re-attestation before stronger runtime claims can be made.

## What is not yet proven

- guest TCP/IP roundtrip: not yet proven; depends on #745
- MLP.PRG actually started inside Mega-ST guest: not yet reobserved for this terminal chain
- Firefox process actually launched as consequence of that guest request: not yet reobserved
- Firefox GUI/terminal actually observed: not yet reobserved
- protected external effect: not claimed
- `EFFECT_ACK_DONE`: not claimed
- physical Mega ST execution: not claimed

## Causal proof target

`MLP.PRG visible -> MLP.PRG executed -> guest TCP/IP -> bound request -> Firefox launched -> terminal loaded -> Effect-Ack discovery -> prepare -> commit -> effect reobserved -> receipt`

Each arrow requires its own evidence. Host networking is not guest networking; a Firefox process is not terminal observation; HTTP success is not Effect Ack.
