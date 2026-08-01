<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Evidenz- und Geltungsgrenze

## Kernelgeprüft

Lean 4.19.0 hat 21 ausdrücklich bezeichnete Sätze des endlichen Modells
kompiliert. Der Receipt weist für jeden Satz die verwendeten foundational
axioms `propext` beziehungsweise `Quot.sound` oder eine leere Liste aus. Es
wurde kein `sorryAx` und kein projektspezifisches Axiom beobachtet.

Bewiesen sind insbesondere Mitgliedschaftserhaltung, die Mengenalgebra des
Merge, bedingte Replica-Konvergenz, Monotonie evidenzgeschlossener Antworten,
corpus-relative Digest-Neuheit, Konfliktbewahrung, Beobachtungs- und
Digital-Twin-Gates, endliche Singleton-Segmentierung und proposal-only
Nichtwirkung.

## Implementiert und getestet

`tools/qikvrt_scientific_fact_growth.py` validiert strikt strukturierte
Claim-Envelopes. Zehn Negativ- und Positivtests belegen im lokalen Stand:

- Klassifikations-/Statusbindung;
- notwendige Lean-Receipts für `FORMAL_PROVED`;
- Beobachtungsenvelopes für `EMPIRICALLY_EVIDENCED`;
- eindeutige Abhängigkeiten;
- corpus-relative syntaktische Neuheit;
- Konflikt- und Identifierbewahrung;
- kommutativen deterministischen Merge; und
- ausnahmslos `EFFECT_ACK_CONTINUE` ohne Publikationsfreigabe.

Diese Tests belegen die getestete Implementierung, nicht ihre universelle
Fehlerfreiheit oder wissenschaftliche Wahrheit der Eingaben.

## Quellengebunden

Die zweite Audioaufnahme ist über SHA-256, Größe und Dauer gebunden. Roh-ASR,
Lesefassung und Interpretation sind getrennt. Die Aufnahme wird nicht als
Messbeleg für ihre eigenen Aussagen behandelt und ist nicht Teil des
Repository- oder Zenodo-Kandidaten.

## Interpretation

Der Begriff `Kausalitätsspiegel` bezeichnet eine nachvollziehbare Abbildung
von Beobachtung, Transformation, Hypothese, Entscheidung, Sollwirkung und
beobachteter Wirkung. Er bedeutet nicht, dass ein Repository allein physische
Ursachen identifiziert.

## Offen

Ausdrücklich offen bleiben:

- universelle Wahrheit und globale wissenschaftliche Neuheit;
- vollständige Natural-Language-to-Lean-Automation;
- Antworten auf jede erdenkliche Frage;
- empirische kognitive Verbesserung aller Nutzenden;
- vollständiger Speicher des gesamten menschlichen Wissens;
- physikalische Zukunft-zu-Vergangenheit-Übertragung;
- VRT-Emergenz, Quanten-zu-Klassik-Limes und physikalische Brücke;
- realer QPU-End-to-End-Nachweis;
- reale Digital-Twin- oder Aktorsicherheit ohne Systemvalidierung;
- IETF-Einreichung, RFC-Status, IETF-Konsens;
- Zenodo-Publikation des neuen Kandidaten;
- EU-AI-Act-Konformitätsbewertung oder Zertifizierung; und
- repositoryweites `PASS`, `FINAL_PASS` oder `EFFECT_ACK_DONE`.

## Persistenzgrenze

Repository, Zenodo und IETF sind getrennte Wirkungsebenen. Zenodo kann
Identität, Metadaten, Verfügbarkeit und Fixität der deponierten Bytes belegen;
es beweist weder Peer Review noch Wahrheit. Ein Internet-Draft bleibt ein
Arbeitsdokument und ist kein RFC. Der neue Kandidat benötigt nach vollständiger
Byte-Freeze eine frische, exakt hashgebundene Autorisierung.
