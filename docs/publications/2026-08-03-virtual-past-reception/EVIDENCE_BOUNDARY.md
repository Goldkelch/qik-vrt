<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Evidenz- und Geltungsgrenze

## Was diese Notiz leistet

Die Notiz persistiert einen autorenseitigen Aphorismus und macht seine
epistemische Lesart explizit. Sie trennt eine semantische Referenz auf ein
früheres Ereignis von einer möglichen heutigen Kausalwirkung der Rezeption.

## Was sie nicht beweist

- keine physikalische oder ontische Retrokausalität;
- kein kontrollierbares rückwärts oder überlichtschnell übertragenes Signal;
- keine Änderung eines früheren Ereignisses;
- keine Wahrheit, Vollständigkeit oder authentische Autorschaft eines Buchs,
  Films, einer Datei oder eines Records;
- keinen kausalen Einfluss eines konkreten Artefakts auf eine konkrete
  Entscheidung ohne gesonderte Evidenzbrücke;
- keine neue empirisch unterscheidbare Vorhersage über die Beschaffenheit der
  physikalischen Realität;
- keinen neuen Lean-Satz und keine Erweiterung vorhandener Kernel-Receipts.

## History- und Persistenzgrenze

Die unqualifizierte Invariante `History ist nach record_created unveränderlich`
ist zu stark. Git-Refs, erreichbare Historien, Speicher und externe Dienste
können umgeschrieben oder gelöscht werden. Stabil gebunden sind, unter den
Kollisionsresistenzannahmen des benannten kryptografischen Algorithmus, die
Identität der durch den Digest bezeichneten Bytes und die Vorgängerrelation
innerhalb einer ausdrücklich immutable definierten Record-Version. Das ist
keine mathematische Injektivitätsgarantie. Ein externer, unabhängiger Anker
kann Umschreiben erkennbar machen, verhindert es aber nicht notwendig.

## EFFECT_ACK-Grenze

Revision `-03` des Effect-Acknowledgement-Entwurfs enthält die einschlägige
Regel bereits: Neue Evidenz, Policy oder Entscheidungen erzeugen eine neue,
verkettete Record-Version. Ein späterer nicht freigebender Record kann nur eine
künftige Freigabe widerrufen; er macht keinen bereits ausgeführten Effekt
ungeschehen.

`INTERPRETATIVE`, `SOURCE_BOUND` und `OPEN` sind Claim-Klassen, keine
EFFECT_ACK-Zustände. Keine dieser Klassen impliziert `EFFECT_ACK_CONTINUE`,
`EFFECT_ACK_DONE` oder einen anderen Zustand. Ohne vorgeschlagenen
nachgelagerten Effekt ist EFFECT_ACK nicht anwendbar.

## Zenodo-Disposition

Der veröffentlichte Record `10.5281/zenodo.21711193` behandelt bereits
kanonischen zeitlichen Speicher, operationale Protokoll-Retrokausalität und die
Nichtbehauptung physikalischer Rückwärtssignalisierung. Der neue Aphorismus ist
eine anschauliche Verdichtung, kein neues empirisches Resultat. Deshalb wird
weder ein neuer Zenodo-Record noch eine neue Version erzeugt.

Eine spätere materiell überarbeitete Fachfassung könnte als neue Version unter
Concept DOI `10.5281/zenodo.21711192` vorbereitet werden. Das setzte eine
sichtbare Änderungsnotiz, eine vollständige Claim-Matrix-Differenz, neue
Machine-Proof- und Prepublication-Receipts sowie eine gesonderte exakte
Publikationsautorisierung voraus.

## IETF-Disposition

Die Aussage erfordert keine Änderung von Wire-Version 1, CDDL, Zuständen,
Priorität oder DONE-Prädikat. Der aktive individuelle Internet-Draft `-03`
enthält die benötigte normative Regel und die physikalische Nichtbehauptung.
Eine Revision `-04` wird deshalb nicht allein für diese Notiz eingereicht.

Falls später ohnehin eine Revision entsteht, kann eine nichtnormative
Erläuterung gebündelt werden. Sie bleibt von jeder normativen Wire- oder
Release-Semantik getrennt.

## Artefaktgrenze

Persistiert wird ausschließlich der vom Autor gelieferte Text. Ein behauptetes
Poster mit der Kennung `wa_image_8838870715819603708` liegt nicht als
auflösbare, byteprüfbare Datei vor. Für dieses Bild wird weder Existenz im
Repository noch SHA-256-Bindung beansprucht.
