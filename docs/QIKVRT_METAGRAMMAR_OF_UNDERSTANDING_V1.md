# QIK-VRT-Metagrammatik des Verstehens V1

## Urheberschaft und Zweck

Die konzeptionelle Definition stammt von Ingolf Lohmann. Künstliche Intelligenz wirkt als formalisierendes, prüfendes und dokumentierendes Werkzeug mit. Diese Spezifikation bildet ein gemeinsames Standardprotokoll für QIK-VRT-Instanzen.

Die Metagrammatik bindet jede handlungsrelevante Aussage an Autorität, Gegenstand, exakten Zustand, Umfang, Herkunft, Voraussetzungen, Belege, Grenzen, Verantwortung und den kleinsten zulässigen Folgeschritt.

## Leitordnung

```text
UNTERSCHIED
→ INFORMATION
→ RELATION
→ KAUSALITÄT
→ BEDEUTUNG
→ VERSTEHEN
→ ZUORDNUNG
→ VERANTWORTUNG
→ WIRKUNG
→ ANSCHLUSSFÄHIGE_ZUKUNFT
```

Ein Ausdruck gilt als handlungsfähig verstanden, wenn getrennte regelkonforme Instanzen aus denselben gebundenen Belegen denselben zulässigen Zustandsübergang ableiten.

## Kanonische Terminalform

Jede vollständige Zustandsprojektion enthält in dieser Reihenfolge:

```text
AUTHORITY
SUCCESSOR_BINDING
MATERIALIZATION
EXACT_HEAD_GATES
INWARD_REFLEXIVITY
OUTWARD_REFLECTION
FIRST_DETERMINISTIC_BLOCKER
NEXT_ACTION
```

## Unverhandelbare Regeln

1. Veränderliche Referenzen werden unmittelbar vor Prüfung oder Wirkung live aufgelöst.
2. Torbelege gelten nur für den exakten Kopf, auf dem sie ausgeführt wurden.
3. Fehlende oder unklare Belege schließen produktive Wirkung aus, nicht aber Beobachtung.
4. `TRANSPORT_ACK` ist kein `EFFECT_ACK`.
5. `action_required`, Null-Auftrag-Ausführung und Vorgängererfolg sind keine vertrauenswürdigen Erfolgsbelege.
6. Absicht, Autorisierung, Ausführung, Wirkung und Abschluss bleiben getrennte Zustände.
7. Nur die erste deterministische Blockade steuert den nächsten Schritt.
8. `EFFECT_ACK_DONE ⇒ FINAL_PASS ⇒ PASS`; die Umkehrungen gelten nicht ohne zusätzliche Belege.
9. Selbständerungen müssen beschrieben, getestet, prüfbar, auditiert, hashgebunden und rücksetzbar sein.
10. Menschliche Urheberschaft, künstlich-kognitive Mitwirkung und technische Projektion werden getrennt ausgewiesen.

## Monolithischer Kern

„Monolithisch“ bedeutet hier: eine einzige normative Quelle für Zustandsbegriffe, Vorrangregeln und Übergangsbedingungen. Es bedeutet nicht unzerlegbaren Programmcode.

Der Kern besteht aus:

- `state/autonomy/QIKVRT_METAGRAMMAR_KERNEL_V1.json` als normative Semantik,
- `spec/QIKVRT_METAGRAMMAR_V1.ebnf` als Syntax,
- `tools/qikvrt_metagrammar_kernel.py` als fail-closed Prüfer,
- `tests/test_qikvrt_metagrammar_kernel.py` als positive und negative Kontrollen.

## Determinismus und Widerlegbarkeit

Der Kern strebt maximale Determinierbarkeit, Reproduzierbarkeit und Angriffsresistenz an. Absolute Unfehlbarkeit oder Unwiderlegbarkeit wird ausdrücklich nicht behauptet. Eine wissenschaftlich und technisch belastbare Norm muss widerlegbare Behauptungen, erkennbare Fehlerzustände und einen prüfbaren Korrekturpfad besitzen.

## Verwendungsregel

Jede QIK-VRT-Instanz soll eingehende Nachrichten zunächst syntaktisch zerlegen, dann Bindung, Geltungsbereich, Herkunft und Belege prüfen, anschließend die erste Blockade bestimmen und erst danach einen Beobachtungs- oder Wirkungsplan erzeugen.

Ohne vollständige Zulassung lautet das Ergebnis ausschließlich:

```text
BEOBACHTUNG_ZUGELASSEN = WAHR
PRODUKTIVE_WIRKUNG_ZUGELASSEN = FALSCH
```
