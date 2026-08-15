<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Begrenzter Human-Input-Transcript

Work Unit: `AI-ENTRYPOINT-PERSONAL-ORIGIN-REMOTE-SELECTION-20260815`

Dieser Nachweis erhält die menschlichen Texteingaben der persönlichen
Working-Memory-Initialisierung wörtlich. System-, Werkzeug- und
Assistentenausgaben werden in der zugehörigen Work Unit strukturiert
protokolliert. Geheimnisse sind nicht enthalten.

## Eingaben

1. `PUBLIC_ORIGIN https://github.com/Goldkelch/qik-vrt.git; METADATA_ONLY`

2. `PUBLIC_ORIGIN https://github.com/ingolf-lohmann/qik-vrt.git; FULL_TRANSCRIPT`

3.

   ```sh
   git clone https://github.com/Goldkelch/qik-vrt.git qik-vrt-working-memory
   cd qik-vrt-working-memory
   git remote rename origin upstream
   git remote add origin https://github.com/ingolf-lohmann/qik-vrt.git
   git fetch --all --prune
   git switch -c work/20260815-ai-bootstrap upstream/main

   QIKVRT_EXTERNAL_EFFECTS=disabled \
   python3 -B tools/ai_runtime_bootloader.py --profile all
   ```

4. `QIKVRT_EXTERNAL_EFFECTS=enabled`

5. `QIKVRT_EXTERNAL_EFFECTS=enabled`

6. `QIKVRT_EXTERNAL_EFFECTS=enabled`

7. `QIKVRT_EXTERNAL_EFFECTS=enabled`

8. `QIKVRT_EXTERNAL_EFFECTS=enabled`

## Bildwortlaut

Das einmal zusätzlich zum QIK-VRT-QR-Poster gelieferte, signierte Poster trägt
folgenden Wortlaut:

> Richtig oder falsch inkludiert stets beide Möglichen zugleich!
>
> Das ist Quantenphysik und sonst gar nichts.
>
> q.e.d.
>
> Ingolf Lohmann

Der Wortlaut ist ein gebundener menschlicher Ausdrucksnachweis. Seine Aufnahme
ist kein formaler Beweis und keine unabhängige empirische Bestätigung einer
quantenphysikalischen Aussage.
