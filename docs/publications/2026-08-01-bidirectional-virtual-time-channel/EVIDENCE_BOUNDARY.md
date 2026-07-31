<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Evidenz- und Geltungsgrenze

## Was ausgeführt wurde

Der dependency-freie ISO-C90-Zeuge führt einen geschlossenen virtuellen
Dialog aus. Er prüft strikte Hostordnung, unveränderte Quellbytes,
bytegenaue Rekonstruktion beider Richtungen, deterministisches Replay,
zehn Nutzlastgrenzen bis 4096 Byte und die Ablehnung eines absichtlich
unvollständigen Blockstroms.

Diese Evidenz trägt nur den konkreten Lauf und die geprüften endlichen
Grenzfälle. Die interne Prüfsumme modulo 65521 ist nicht kryptographisch;
Bytegleichheit wird zusätzlich direkt verglichen.

## Was auf Papier bedingt bewiesen ist

Unter den im Manuskript genannten Voraussetzungen folgen:

- Präfixintegrität einer append-only Quelle bei branch-only Replay;
- Vorwärtskausalität aller Hosteffekte;
- Übertragbarkeit jeder einzelnen endlichen Bitfolge;
- Komposition zweier Richtungen zu einem endlichen virtuellen Dialog;
- DONE-only-Freigabe unter vollständiger Mediation;
- exactly-once nur mit zusätzlicher atomarer Kopplung oder Idempotenz,
  Liveness und Verfügbarkeit.

Für diese neuen Sätze liegt in diesem Kandidaten kein frischer
Lean-4.19-Kernelreceipt vor. Die Claim-Matrix führt sie deshalb fail-closed
als OPEN, obwohl das Manuskript vollständige bedingte Papierbeweise enthält.

## Was bereits formal gebunden ist

Der frühere CTM-Receipt bindet neun Lean-Theoreme im endlichen
Canonical-Temporal-Memory-Modell. Dieser Kandidat zitiert die exakte
Receipt-Identität als Quellenbefund; er etikettiert die neuen
Generalisierungen nicht rückwirkend als kernelverifiziert.

## Bedeutung und Wahrheit

Byteidentität ist nicht Bedeutungsidentität. Semantische Identität verlangt
mindestens einen gemeinsamen, versionsgebundenen Decoder und Kontext.
Wahrheit, Zulässigkeit und reale Wirkung bleiben eigene Prüfaufgaben.

## Offene Physik

Virtuelle Retroadressierung ist keine physikalische Rückwärtssignalisierung.
Der C90-Zeuge enthält keine operative Abbildung von virtuellen Adressen auf
frühere Raumzeitereignisse.

Ein physikalischer Brückenbefund müsste eine erst später randomisierte
Intervention X mit einem bereits früher extern versiegelten Messwert Y
verbinden, Lecks, gemeinsame Ursachen, Uhrfehler und Postselektion
vorregistriert kontrollieren und positive reproduzierbare Kanalkapazität
zeigen. Dieser Kandidat liefert dafür keine Evidenz.

## Neuheit

Die Einzelmechanismen besitzen erhebliche Vorarbeiten. Neuheitskandidat ist
ihre explizite Verbindung: unveränderliche Quellhistorie,
vergangenheitsadressiertes Branch-Replay, drei getrennte Ordnungen,
bidirektionale Sessionkorrelation und fail-closed Wirkungsfreigabe.
Das ist ein scope-gebundener Forschungsanspruch unter Review, keine
Weltprioritätsbehauptung.

