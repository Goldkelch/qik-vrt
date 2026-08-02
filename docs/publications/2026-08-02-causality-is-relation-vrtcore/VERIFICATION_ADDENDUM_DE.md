<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Verifikationsnachtrag: vom formalen Kandidaten zum bytegenau geprüften Kernelstand

## Status dieses Nachtrags

Dieser Nachtrag verändert den ursprünglichen Artikel, die ursprüngliche
WhatsApp-/Vorlesefassung und die zurückgegebene H0-Claim-Matrix nicht. Er fügt
eine belegte H1-Transition hinzu: Genau die 21 dort als formale Kandidaten
ausgewiesenen Aussagen T01–T21 wurden für die gebundenen Quelldateien durch
Lean 4.19.0 akzeptiert. Alle physikalischen, empirischen, interpretativen,
normativen und offenen Aussagen behalten ihren bisherigen Erkenntnisstatus.

`PASS` gilt hier ausschließlich für diesen formalen Kernelumfang.
`GLOBAL_PASS`, `FINAL_PASS` und `EFFECT_ACK_DONE` werden nicht beansprucht.

## Das verifizierte Ergebnis

Der GitHub-Actions-Lauf `30732070295` führte den Lean-Kandidaten und seinen
Axiom-Audit mit Exitcode 0 aus. Das erhaltene Artefakt
`8828292691` hat den Archiv-Digest
`sha256:30ab2ac64e444bcf48c443bc49e686e633a5a6de11c2ed6b9699f9327f377fab`.
Sein unverändert erhaltenes JSON-Mitglied liegt als
`CI_KERNEL_EVIDENCE_H0_PR_MERGE.json` im Bundle.

Das Ergebnis lautet:

- 21 von 21 benannten Theoremen wurden vom Lean-4.19.0-Kernel akzeptiert.
- 15 Theoreme weisen im Axiom-Audit keine Axiomabhängigkeit aus.
- 6 Theoreme hängen ausschließlich von Leans grundlegendem `propext` ab:
  T01, T12, T13, T14, T15 und T19.
- Es gibt keine projektdefinierten Axiome und für diese exakten Quellen keine
  Ausweichbeweise durch `sorry`, `admit` oder `unsafe`.
- Importiert wird ausschließlich `Std`.

Die verifizierten Quellen sind bytegenau gebunden:

- Lean-Kandidat: 12.301 Bytes,
  SHA-256 `1a39cd338f543f642acf634ffb2b63cd2c1a2ffe92878208f48d71a68a8e7d22`.
- Axiom-Audit: 1.575 Bytes,
  SHA-256 `5d3ceb24125acd41b34725e485ab0a4f4f61492273cf60b6973c9851da7eabb7`.

Der vollständige, maschinenlesbare Beleg steht in
`KERNEL_RECEIPT_H0_CI.json`; die daraus abgeleitete, fail-closed formulierte
Statusänderung steht in `VRTCore_CLAIM_MATRIX_H1_KERNEL_VERIFIED.json`.

## Exakte Git-Grenze

`source_bytes_exact=true` ist gerechtfertigt: Artefakt, Quell-Digests,
Blob-Identitäten und beide erfolgreichen Lean-Schritte stimmen überein.

`repository_head_exact=false` bleibt ebenso zwingend. Der Lauf wurde durch ein
`pull_request`-Ereignis ausgelöst und checkte den synthetischen Merge-Commit
`fc0b05cd13d7607883fbab9f16b4628f77a0958c` aus. Der Workflow-Datensatz nennt
daneben `head_sha=987e4a6f163562bba32ea7575c41013c91a0b6a1`. Das im CI-Artefakt gesetzte
`exact_head_bound=true` wird deshalb ausschließlich als exakte Bindung an den
ausgeführten PR-Merge-Checkout verstanden — nicht als Beleg für einen aktuellen
Branch-Head, `main`, den gesamten Repositoryzustand oder eine spätere Fassung.

## Wissenschaftliche Konsequenzen

Die zentrale wissenschaftliche Konsequenz ist nicht, dass nun eine neue Physik
bewiesen wäre. Sie ist präziser und für ein Forschungsprogramm entscheidend:
Ein Teil der These wurde aus bloßer Prosa in eine explizite, typisierte und
maschinell prüfbare Struktur überführt.

Für den exakt gebundenen VRTCore-Kandidaten ist jetzt kernelgeprüft, dass:

1. sechs Erkenntnisarten im formalen Datentyp unterscheidbar sind;
2. eine beobachtete Sequenz und eine Relation mit expliziter Brücke verschiedene
   Beweiskonstruktoren sind;
3. eine positive syntaktische Kausalitätslizenz eine solche Brücke verlangt;
4. technischer Erfolg und autorisierte Außenwirkung getrennte Zustände bleiben;
5. additive Rekursion frühere Felder erhält und diese Erhaltung transitiv ist;
6. ein klassischer Minkowski-Grenzkandidat nur bei *vorgelegter* Stabilität und
   *vorgelegtem* vierdimensionalem Zeugen zugelassen wird.

Damit ist die Grammatik des Behauptens schärfer geworden: Eine Reihenfolge darf
nicht unbemerkt als Ursache ausgegeben werden, ein Exitcode darf nicht als
verantwortete Freigabe gelten, und ein konditional gelieferter Raumzeitzeuge
darf nicht als hergeleitete Raumzeit erscheinen. Diese Trennungen sind jetzt
für T01–T21 nicht nur redaktionelle Absicht, sondern Kernelresultat.

Die EBNF-Grammatik und ihre Regeln S01–S15 bleiben ein eigenständiger
maschineller Vertrag. Der offene Parser-Auftrag wird durch den Lean-Beleg nicht
geschlossen: Dafür fehlen weiterhin ein ausführbarer Parser, Positiv- und
Negativkorpus, deterministische AST-Tests und Statuserhaltungstests. Ebenso
offen bleiben eine konstruktive Minkowski-Emergenz, der Übergang zu allgemeinen
lorentzschen Raumzeiten und eine quantitative empirische Brücke.

## Menschliche Konsequenzen

Die menschliche Bedeutung liegt in einer überprüfbaren Form von Verantwortung.
Wissen wird nicht nur erzeugt, sondern mit Herkunft, Grenze, Unsicherheit,
Widerspruch, Wirkung und Autorisierung verbunden. Das schafft Bedingungen,
unter denen Menschen Aussagen prüfen, korrigieren, ablehnen oder bewusst
weiterführen können, ohne dass technische Durchführung bereits als Zustimmung
ausgegeben wird.

Gerade deshalb darf hier klar gesagt werden: **Das ist eine großartige
Leistung.** Ingolf Lohmann hat eine weit gespannte Intuition nicht bei einer
starken Formulierung stehen lassen, sondern sie in Artikel, Vorlesefassung,
Claim-Matrix, Semantik, Syntax, Lean-Quelltext, Axiom-Audit und reproduzierbare
Provenienz übersetzt. 21 formale Aussagen dieses Kerns sind nun exakt gebunden
und maschinell akzeptiert. Dieser Stolz ist kein Ersatz für Evidenz; er wird
durch die geleistete Übersetzungs-, Begrenzungs- und Prüfarbeit begründet.

Die Würdigung bleibt dennoch eine normative Bewertung. Sie behauptet weder
Fachkonsens noch abgeschlossene Physik noch unabhängiges Peer Review. Ihre
Glaubwürdigkeit entsteht gerade daraus, dass die offenen Lücken sichtbar
bleiben.

## Was ausdrücklich nicht folgt

Aus diesem CI-Kernelbeleg folgt nicht:

- dass die Natur fundamental VRTCore folgt;
- dass physische Rückwärtskausalität oder Rückwärtssignalisierung möglich ist;
- dass Prozessmatrizen oder der Quantum Switch die Gesamtthese empirisch
  bestätigen;
- dass Minkowski- oder allgemeine lorentzsche Raumzeit konstruktiv emergiert;
- dass die EBNF bereits durch einen Referenzparser vollständig implementiert ist;
- dass unabhängiges Peer Review oder wissenschaftlicher Konsens vorliegt;
- dass GitHub-Persistenz, IETF-Einreichung oder Zenodo-Publikation durch diesen
  Beleg erfolgt, freigegeben oder bestätigt wurde.

GitHub-CI, IETF und Zenodo bleiben getrennte Wirkungskanäle mit jeweils eigenen
Receipts und Autorisierungen. Technischer Erfolg ist ein notwendiger Beleg für
den technischen Schritt — niemals allein die verantwortete Freigabe seiner
Außenwirkung.

## H0 → H1 in einem Satz

H0 bewahrte 21 ungeprüfte formale Kandidaten; H1 stuft genau diese 21 Aussagen
auf `FORMAL_PROVED_KERNEL_VERIFIED` hoch, weil Lean 4.19.0 die exakt gebundenen
Bytes akzeptiert hat — und lässt jede weitergehende wissenschaftliche oder
menschliche Deutung dort, wo sie epistemisch hingehört.
