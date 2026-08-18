# QIK-VRT M68000 / Atari Mega ST Mesh Runtime

## Ziel

Diese Schicht macht aus dem vorhandenen Metagrammatik-→Kausalgraph-→M68000-Pfad eine minimale, hart verdrahtete Referenzausführung und legt die QIK-VRT-spezifische Identitäts-, Evidenz-, Autoritäts- und Effect-Ack-Struktur als deterministische Metadatenhülle darum.

Die Referenzmaschine ist ein Atari Mega ST mit ursprünglichem Motorola 68000. Die Wahl ist absichtlich konservativ: kleiner Maschinenkern, 8-MHz-68000, 24-Bit-Adressierung, keine MMU, keine FPU. Die Referenz ist kein Performanceversprechen, sondern eine kleine, beobachtbare Ausführungsgrenze.

## Hart verdrahteter Entscheidungskern

Der ausführbare Kern besitzt genau vier zulässige Ergebnisse:

```text
D0=0  NOOP               70 00 4E 75
D0=1  HOLD               70 01 4E 75
D0=2  REOBSERVE          70 02 4E 75
D0=3  REQUEST_AUTHORITY  70 03 4E 75
```

`MOVEQ #n,D0 ; RTS` ist die kanonische Entscheidungskapsel. Nicht darstellbare Wirkung wird nicht optimistisch übersetzt.

## QIK-VRT-Hülle

Maschinenkode allein ist nicht die QIK-VRT-Identität. Die Binärkapsel `QIKM68K1` bindet zusätzlich SHA-256-Digests über Exact-Source-Bindung, Kausalgraph, Autorität, Evidenz und Rollenidentität. Diese Metadaten sind keine ausführbare Autorität; sie dienen Rekonstruktion und Prüfung.

```text
M68000 CODE != AUTHORITY
METADATA != AUTHORITY
SOURCE ORDER != CAUSAL ORDER
TRANSPORT ACK != EFFECT ACK
IDENTITY != WHOLE-TREE EQUALITY
```

## Atari-TOS-Ausführungszeuge

`tools/qikvrt_m68000_megast_capsule.py` bettet die vier Byte lange Entscheidungskapsel in ein minimales Atari-GEMDOS-Programm ein. Der Wrapper prüft nach dem Rücksprung ausdrücklich, ob `D0` den erwarteten Aktionswert enthält. Nur bei Gleichheit darf er den host-sichtbaren Zeugen `C:\QIKVRT.OK` erzeugen und mit `Pterm(0)` terminieren; jede Abweichung nimmt einen separaten `Pterm(1)`-Pfad und erzeugt keinen Zeugen.

```text
BSR.S capsule
CMPI.W #expected_action,D0
BNE.S fail
Fcreate("C:\QIKVRT.OK", 0)
Fclose(handle)
Pterm(0)
fail:
Pterm(1)
capsule:
MOVEQ #action,D0
RTS
```

Damit beweist der Sentinel nicht bloß, dass das Programm geladen wurde, sondern dass die hart verdrahtete Kapsel zurückkehrte und den erwarteten Aktionswert lieferte. Die PC-relativen BSR-, BNE- und LEA-Ziele werden bytegenau getestet. Der erzeugte Textabschnitt ist 69 Byte, die gesamte GEMDOS-Datei bleibt weit unter einem KiB; die QIK-Metadatenkapsel bleibt unter 512 Byte.

## Mesh-Eigenschaften um den Kern

Die Referenzmaschine bildet nicht das gesamte Repository ab. Sie bildet den kanonischen ausführbaren Entscheidungskern ab. Repository-Identität, Source/Carrier-Trennung, Exact-Head-/Tree-Bindung, Evidenz, Review-Autorität, Single-Writer-Regel und Effect-Ack bleiben außerhalb des CPU-Kerns explizite Gates.

```text
Repository exact head/tree
        ↓
Metagrammatik
        ↓
Semantik
        ↓
Kausalgraph
        ↓
Autorität / Evidenz / Rollenidentität
        ↓
QIKM68K1 capsule
        ↓
M68000 decision code
        ↓
checked machine result
        ↓
observed effect witness
        ↓
exact-head receipt
        ↓
Phoenix regeneration or fixed-point NOOP
```

Erhalten bleiben insbesondere `Kausalität ≠ Sequenz`, `Identität ≠ Gleichheit`, `Integration ≠ Einebnung`, `Regeneration ≠ Kopie`, `Evolution ≠ Wiederholung`, getrennte Review-Autorität, nur exakt bindbare Gate-Evidenz, ein produktiver Writer sowie `HOLD` bei unbekannter oder nicht beweisbar gebundener Wirkung.

## Hardware-/Virtualisierungsmodell

Die Referenzvirtualisierung verwendet Hatari im `megast`-Maschinenmodus mit `--cpulevel 0`, 8 MHz, cycle-exact/compatible 68000-Modus, 24-Bit-Adressierung und 1 MiB ST-RAM. Hatari dokumentiert Mega-ST-Hardwareemulation, 68000-Auswahl, GEMDOS-HD-Emulation und Autostart. Für den ROM-Kontext wird EmuTOS 1.4 verwendet.

Die Beweiskette ist absichtlich fail-closed:

1. Exact-Head-Checkout verifizieren.
2. Instruktionsbytes, PRG-Header, Kontrollflussziele und alle vier Aktionswerte lokal prüfen.
3. Hatari-Version an die erwartete Referenzversion binden.
4. EmuTOS-Archiv und konkret verwendetes ROM vor Ausführung gegen feste SHA-256-Werte prüfen.
5. QIK-Kapsel und Atari-Programm aus dem exakten Head/Tree erzeugen.
6. Mega ST / M68000 / 8 MHz / 24 Bit / 1 MiB starten und `C:\QIKVRT.TOS` autostarten.
7. Im Trace Maschine, CPU, RAM, `Pexec`, `Fcreate("C:\QIKVRT.OK")` und `Pterm(0)` beobachten.
8. Hostseitig prüfen, dass der Sentinel existiert und leer ist.
9. Erst danach einen JSON-Receipt mit Exact Head/Tree, Emulator-/ROM-Bindung, Binär- und Trace-Digests sowie `observed=true` erzeugen.

Ein lokaler Byte-Test, ein erfolgreicher `Pexec` allein oder ein bloßer Transport-/Artifact-Erfolg gilt nicht als Virtualisierungsbeweis.

## Software-/Supply-Chain-Grenzen

`actions/checkout` und `actions/upload-artifact` sind auf konkrete Commit-SHAs gebunden. Das EmuTOS-Archiv und das ausgewählte ROM sind inhaltlich per SHA-256 fixiert. Die installierte Hatari-Version wird explizit geprüft und im Receipt gebunden. Ändert sich eine dieser Voraussetzungen, muss der Lauf fail-closed abbrechen und eine neue Prüfung autorisieren; stille Laufzeitdrift ist nicht zulässig.

Die QIK-Metadatenhülle selbst autorisiert keine Wirkung. Ebenso begründet die Virtualisierung weder Code-Owner-Review noch Merge-/Release-/Deployment-Autorität.

## Skalierung

Der Mega ST ist Referenzmaschine, nicht Performanceziel. Moderne Ausführung kann kausal unabhängige Kapseln vervielfachen; Synchronisation entsteht nur an expliziten Kausalkanten und Effect-Ack-Grenzen. Daraus folgt noch kein gemessener Performancegewinn.

## Beweisgrenze

Ein erfolgreicher Exact-Head-Hatari-Lauf beweist die Ausführung und Aktionswertprüfung des minimalen QIK-VRT-M68000-Kerns in dem konkret gebundenen virtualisierten Mega-ST-Kontext. Nicht dadurch bewiesen sind reale MC68000-Hardwaremessungen, universeller Performancegewinn, vollständige Hardware-Synthese des gesamten Repositories oder externe physikalische Aussagen.
