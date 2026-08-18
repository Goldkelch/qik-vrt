# QIK-VRT M68000 / Atari Mega ST Mesh Runtime

## Ziel

Diese Schicht macht aus dem vorhandenen Metagrammatik-→Kausalgraph-→M68000-Pfad eine minimale, hart verdrahtete Referenzausführung und legt die QIK-VRT-spezifische Identitäts-, Evidenz-, Autoritäts- und Effect-Ack-Struktur als deterministische Metadatenhülle darum.

Die Referenzmaschine ist ein Atari Mega ST mit ursprünglichem Motorola 68000. Die Wahl ist absichtlich konservativ: kleiner Maschinenkern, 8-MHz-68000, 24-Bit-Adressierung, keine MMU, keine FPU. Die QIK-VRT-Semantik soll auf einer kleinen historischen Maschine erklärbar und ausführbar bleiben und auf heutiger Hardware beliebig oft als unabhängige kausale Projektion instanziiert werden können.

## Hart verdrahteter Entscheidungskern

Der ausführbare Kern besitzt genau vier zulässige Ergebnisse:

```text
D0=0  NOOP               70 00 4E 75
D0=1  HOLD               70 01 4E 75
D0=2  REOBSERVE          70 02 4E 75
D0=3  REQUEST_AUTHORITY  70 03 4E 75
```

`MOVEQ #n,D0 ; RTS` ist die kanonische Entscheidungskapsel. Ein fünfter produktiver Effekt wird nicht stillschweigend abgebildet. Nicht darstellbare Wirkung endet fail-closed.

## QIK-VRT-Hülle

Maschinenkode allein ist nicht die QIK-VRT-Identität. Die Binärkapsel `QIKM68K1` bindet zusätzlich SHA-256-Digests über:

1. Exact-Source-Bindung;
2. Kausalgraph;
3. Autorität;
4. Evidenz;
5. Rollenidentität.

Diese Metadaten sind **keine ausführbare Autorität**. Sie machen den kleinen Maschinenkern rekonstruierbar und prüfbar. Wirkung bleibt an die höheren QIK-VRT-Gates gebunden.

Damit gilt:

```text
M68000 CODE != AUTHORITY
METADATA != AUTHORITY
SOURCE ORDER != CAUSAL ORDER
TRANSPORT ACK != EFFECT ACK
IDENTITY != WHOLE-TREE EQUALITY
```

## Atari-TOS-Programm

`tools/qikvrt_m68000_megast_capsule.py` kann die vier Byte lange Entscheidungskapsel zusätzlich in ein minimales Atari-GEMDOS-Programm einbetten. Der Textabschnitt besteht aus:

```text
BSR.S capsule
MOVE.W D0,-(SP)
MOVE.W #$4C,-(SP)
TRAP #1
capsule:
MOVEQ #action,D0
RTS
```

Der Wrapper übergibt damit den QIK-VRT-Aktionswert als GEMDOS-`Pterm`-Rückgabecode. Der erzeugte TOS-PRG-Text ist 14 Byte lang; die gesamte PRG-Datei bleibt weit unter einem KiB. Die QIK-Metadatenkapsel bleibt ebenfalls unter 512 Byte. Schon eine konservative 1-MiB-Mega-ST-Konfiguration besitzt daher um Größenordnungen mehr Speicher als der Referenzkern benötigt.

## Mesh-Eigenschaften um den Kern

Die Maschine bildet nicht das gesamte Repository ab. Sie bildet den **kanonischen ausführbaren Entscheidungskern** ab. Die Mesh-Eigenschaften liegen als verifizierbare Hülle darum:

```text
Repository exact head/tree
        ↓
Metagrammatik
        ↓
Semantik
        ↓
Kausalgraph
        ↓
Autorität / Evidence / Role identity
        ↓
QIKM68K1 capsule
        ↓
M68000 decision code
        ↓
observed machine result
        ↓
Effect reobservation / receipt
        ↓
Phoenix regeneration or fixed-point NOOP
```

Die folgenden Invarianten bleiben erhalten:

- `Kausalität ≠ Sequenz`;
- `Identität ≠ Gleichheit`;
- `Integration ≠ Einebnung`;
- `Regeneration ≠ Kopie`;
- `Evolution ≠ Wiederholung`;
- Source und Verification Carrier bleiben getrennte Identitäten;
- nur exakt bindbare Gate-Evidenz darf übertragen werden;
- Review-Autorität bleibt separat;
- ein produktiver Writer gleichzeitig;
- unbekannte oder nicht beweisbar gebundene Wirkung => `HOLD`;
- Fixpunkt => `NOOP`, kein Aktivitätscommit.

## Virtualisierungsbeweis

Die Referenzvirtualisierung verwendet Hatari im `megast`-Maschinenmodus mit 68000, 8 MHz und 24-Bit-Adressierung. Hatari dokumentiert Mega-ST-Emulation, 68000-CPU-Emulation, GEMDOS-Harddrive-Emulation und Programm-Autostart. EmuTOS kann als freie TOS-kompatible ROM-Implementierung verwendet werden.

Der CI-Probe ist fail-closed:

1. QIK-Kapsel und TOS-PRG deterministisch erzeugen;
2. Header und Instruktionsbytes lokal prüfen;
3. Hatari/EmuTOS installieren bzw. lokalisieren;
4. `--machine megast --cpulevel 0 --cpuclock 8 --addr24 on` verwenden;
5. Programm über GEMDOS-Laufwerk automatisch starten;
6. CPU-/OS-Trace erzeugen;
7. nur dann `MEGAST_VIRTUAL_EXECUTION_OBSERVED=true` materialisieren, wenn der Emulator tatsächlich den generierten Programmpfad erreicht und die erwartete Entscheidungskapsel in der Ausführungsspur beobachtet wird.

Fehlt Hatari, EmuTOS oder die erwartete Ausführungsspur, bleibt der Zustand `HOLD`; ein lokaler Byte-Test wird nicht als Virtualisierungsbeweis ausgegeben.

## Skalierung

Der Mega ST ist Referenzmaschine, nicht Performanceziel. Moderne Ausführung skaliert durch Vervielfachung **kausal unabhängiger** Kapseln. Synchronisation entsteht nur an expliziten Kausalkanten und Effect-Ack-Grenzen. Das vermeidet die falsche Gleichsetzung von Parallelität mit unkontrollierter Gleichzeitigkeit.

## Beweisgrenze

Mit erfolgreicher Hatari-Ausführung ist bewiesen, dass der minimale QIK-VRT-Entscheidungskern in einem virtualisierten Mega-ST/M68000-Ausführungskontext läuft. Nicht dadurch bewiesen sind reale MC68000-Hardwaremessungen, universeller Performancegewinn, vollständige Hardware-Synthese des gesamten Repositories oder externe physikalische Aussagen.
