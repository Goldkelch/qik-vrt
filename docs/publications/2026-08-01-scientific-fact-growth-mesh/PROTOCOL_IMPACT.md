<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Auswirkung auf EFFECT_ACK und das Beobachtungsprofil

## Ergebnis

Der Scientific-Fact-Growth-Mechanismus ändert die geschlossene Version-1-
Wire-Struktur des bestehenden EFFECT_ACK-Entwurfs nicht. Er ist ein
Anwendungs- und Evidenzprofil oberhalb der vorhandenen Felder
`evidence_refs`, `required_evidence_refs`, `reasons`, `open_questions` und
`next_required_checks`.

## Neue protokollgeeignete Objekte

Ein konformes Anwendungssystem referenziert inhaltsadressierte Objekte für:

- Claim-Envelope;
- Corpus-Snapshot;
- Quell- und Beobachtungsprovenienz;
- Lean-Kernelreceipt;
- Abhängigkeits- und Widerspruchsgraph;
- corpus-relative Neuheitsprojektion;
- Review- und Dispositionsrecord; und
- spätere Effect-Ack- beziehungsweise Effect-Receipt-Objekte.

## Normative Mindestregeln

1. Ein Empfänger, der das Profil beansprucht, MUSS die epistemische Klasse und
   ihren kompatiblen Status unabhängig prüfen.
2. `FORMAL_PROVED` MUSS einen gebundenen Kernelreceipt und eine exakte
   Formalquelle besitzen.
3. `EMPIRICALLY_EVIDENCED` MUSS Methode, Kalibrierung, Unsicherheit,
   Provenienz und Rohdatenidentität ausweisen.
4. `OPEN` DARF NICHT in eine established-fact-Projektion eingehen.
5. Widersprüche und gleiche Identifier mit unterschiedlichen Inhalten DÜRFEN
   NICHT still überschrieben werden.
6. Eine Neuheitsangabe MUSS ihren endlichen Basiskorpus und ihre Methode
   nennen. Digest-Neuheit DARF NICHT als globale wissenschaftliche Neuheit
   bezeichnet werden.
7. Unvollständige, veraltete, nicht authentifizierte oder digestfalsche
   Pflichtobjekte MÜSSEN ordinary release verhindern.
8. Profilkonformität allein DARF `EFFECT_ACK_DONE` nicht erzwingen.

## Bedrohungsmodell

Zusätzliche Risiken sind:

- Epistemic-class laundering: eine Hypothese wird als Messung oder Beweis
  etikettiert;
- proof-receipt substitution: Receipt und Formalquelle gehören nicht zusammen;
- corpus omission: relevante Gegenclaims werden aus dem Neuheitskorpus
  entfernt;
- translation collision: unterschiedliche Aussagen erhalten durch schlechte
  Normalisierung denselben Vergleichsschlüssel;
- model-generated citation fabrication;
- identifier capture durch denselben Claim-ID mit anderen Bytes;
- majority laundering: häufige Replikation wird als Wahrheit ausgegeben;
- private-evidence leakage über zu detaillierte Provenienz; und
- release bypass zwischen Wissensprüfung und Aktor.

## Protokollkandidat

Der getrennte RFCXML-v3-Kandidat
`draft-lohmann-qikvrt-scientific-claim-assurance-00` beschreibt diese Regeln.
Er ist additiv, fordert keine IANA-Aktion und ist nicht beim IETF Datatracker
eingereicht. Eine spätere Einreichung benötigt die endgültigen XML-, TXT- und
HTML-Hashes sowie eine eigene exakte Autorisierung.
