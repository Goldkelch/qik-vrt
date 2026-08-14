<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Fail-closed v3-Finalisierung

## SOURCE

- [x] 17 Kandidaten und 6 Proof-Artefakte ergeben exakt 23 Uploadpfade.
- [x] Text und M4A sind durch Bytes, SHA-256 und Git-Blob gebunden.
- [x] Text bleibt owner-supplied; M4A bleibt untranskribiert.
- [x] `Freigabe!` im Text ist als Inhalt ohne Ausführungswirkung abgegrenzt.
- [x] v2-Steuerung, -Workflow, -Autorisierung und -Manifest bleiben unverändert.
- [ ] kompletter SOURCE-Commit ist remote vorhanden und wurde erneut geprüft.

## Action-time-Autorisierung

- [ ] Product Owner gibt nach dem SOURCE-Commit die in
  `RETURN_TO_OWNER_MESSAGE.md` erzeugte kanonische Zeile exakt zurück.
- [ ] `authorized_at` liegt nach Return- und SOURCE-Commit-Zeit.
- [ ] neue Authorization ID, frischer nicht-null Nonce und v3-Publication-ID.
- [ ] kein v2-Receipt, keine v2-Lock-Ref und kein v3-Replay vorhanden.

## EXECUTION und Workflow

- [ ] `finalize_authorized_controls.py --write` läuft am sauberen SOURCE-Head.
- [ ] ein einzelner Nachfolger-Commit enthält nur die zwei finalen v3-Controls
  und die drei globalen Integritätsprojektionen.
- [ ] ein separater Workflow-Commit bindet SOURCE und EXECUTION exakt.
- [ ] die geschützte v3-Produktionsumgebung und das scoped Secret existieren.
- [ ] erst danach darf ein manueller Dispatch erneut erwogen werden.

Kein Punkt dieser Liste ist selbst eine Produktionsfreigabe.
