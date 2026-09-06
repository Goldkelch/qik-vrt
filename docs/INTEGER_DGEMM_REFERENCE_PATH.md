# FP64-Zielvertrag über INT8-Slices

QIK-VRT enthält nun einen reproduzierbaren Referenzpfad in
`tools/qikvrt_integer_dgemm.py`:

```text
finite binary64
  → signed base-128 INT8 limbs + binary exponent
  → integer product buckets with an INT32 bound
  → binary64 reconstruction and final summation
```

Der Pfad ist absichtlich eine portable Referenzimplementierung und keine
Behauptung nativer INT8-Matrixhardware. Die Eingaben müssen endliche IEEE-754
binary64-Werte sein. Bitidentität mit einer nativen DGEMM und Statusflags sind
kein Bestandteil dieses Vertrags; die Tests prüfen sie daher getrennt von der
numerischen Fehlerbetrachtung. Die aktuelle Referenz verwendet keine
Bibliothek außerhalb der Python-Standardbibliothek.

## Reproduktion

```sh
python3 -B -m unittest -v tests.test_integer_dgemm
python3 -B tools/qikvrt_integer_dgemm.py --benchmark --size 4 --repetitions 3
```

Das Benchmark-JSON bindet Problemgröße, Wiederholungen, Python- und
Plattformangabe sowie beide Messpfade. Laufzeiten sind lokale Messwerte und
keine allgemeine Speedup- oder Energiebehauptung. Für einen Hardwarevergleich
müssen native FP64-DGEMM, dieselbe Eingabeverteilung, identische
Problemgrößen, Softwareversionen und Messmethoden separat gebunden werden.

## QIK-VRT-Nachweisgrenze

```text
Rechenauftrag angenommen
  ≠ Rechenpfad abgeschlossen
  ≠ numerischer Vertrag nachgewiesen
  ≠ physische Wirkung beobachtet
```

Der Referenzpfad weist eine konkrete arithmetische Realisierung nach. Er
autorisiert weder Veröffentlichung noch externe Wirkung und modelliert keine
IEEE-754-Statusflags.
