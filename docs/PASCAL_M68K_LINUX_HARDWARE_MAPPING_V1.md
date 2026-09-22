# Pascal → M68000 Linux: der nächste AD/DA-Hardware-Ring

## Zweck

Diese Tranche nimmt den auf PR #895 reobservierten Pascal-Semantikkern und bildet ihn mit einem realen Cross-Compiler auf Motorola-68000-Maschinenbytes ab. Die Zielplattform ist zunächst `m68k-linux` und nicht Atari/TOS. Dadurch wird die Compiler-/ISA-Brücke isoliert geprüft, bevor ein zweiter Ring das Atari-Dateiformat, TOS und Hatari/EmuTOS bindet.

```text
Pascal semantic receipt
→ pinned Free Pascal source
→ x86_64 bootstrap compiler
→ m68k-linux cross compiler
→ M68K ELF bytes
→ qemu-m68k execution
→ normalized output receipt
```

## Warum Linux vor TOS

Divide-and-Conquer gilt auch für Zielplattformen. Der M68000-Befehlssatz, das Objektformat, der Betriebssystem-ABI, das Loaderformat und die konkrete Maschine sind unterscheidbare Schichten:

```text
Pascal semantics
!= compiler implementation
!= M68000 ISA
!= M68K Linux ABI
!= Atari TOS executable
!= Hatari/EmuTOS execution
!= physical Mega ST execution
```

Die erste Zieltranche isoliert Compiler, ISA und einen ausführbaren ABI. Der nachfolgende Atari-Ring darf dann nur noch die TOS-spezifischen Unterschiede hinzufügen.

## Deterministische Toolchain

Der Cross-Compiler wird aus einem fest gebundenen Commit des offiziellen Free-Pascal-Quellrepositorys gebaut. Der Workflow bindet:

- Bootstrap-Compiler und Version,
- FPC-Quellcommit,
- Ziel-CPU `m68k`,
- Ziel-OS `linux`,
- GNU-M68K-Binutils,
- erzeugten Cross-Compiler-Digest,
- ELF-Maschinenheader,
- Zielbinär-Digests,
- QEMU-Version,
- normalisierte Programmausgabe.

## Beobachtungsgrenze

Beobachtet werden soll:

- reale Erzeugung von M68K-ELF-Maschinenbytes,
- Cross-Kompilation im Turbo-Pascal- und Delphi-Modus,
- Ausführung beider Binärfamilien unter `qemu-m68k`,
- gleiche normalisierte Test- und Shell-Ausgaben wie im Host-Pascal-Receipt,
- getrennte Binärdigests,
- literal-exact-head und exact-tree Receipt-Bindung.

Nicht behauptet werden:

- Atari-/TOS-Binärformat,
- Hatari-/EmuTOS-Ausführung,
- physische Motorola-68000-Ausführung,
- physische Mega-ST-Ausführung,
- historischer Borland-Turbo-Pascal-Compiler,
- Embarcadero Delphi,
- externer Effekt,
- `EFFECT_ACK_DONE`, `PASS` oder `FINAL_PASS`.

## Kausalität

Das sichtbare M68K-Binary ist die Frucht. Seine unsichtbaren Wurzeln sind Pascal-Source-Blob, Parent-Head, Toolchain-Commit, Bootstrap-Compiler, Binutils, Ziel-ABI und Testvektor. Erst das Receipt bindet Frucht und Wurzeln zu einer kausal rekonstruierbaren Compilerwirkung.

q.e.d. — Ingolf Lohmann
