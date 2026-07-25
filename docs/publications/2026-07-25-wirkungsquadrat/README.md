# Das Wirkungsquadrat der Planck-Skala

Repository-native, reproduzierbare Fassung des am 25. Juli 2026 erzeugten
Preprint-Kandidaten von Ingolf Lohmann.

## Identität und Provenienz

- lokaler Vorläufer: `QIKVRT_WIRKUNGSQUADRAT_V1_PRAEPRINT_CANDIDATE_2026-07-25.zip`
- SHA-256 des lokalen Vorläufers: `48a1f4edf1918080dd140529159ce8f98c3b5c10e04112867cf1fe9f3eed9a60`
- SHA-256 des darin enthaltenen 38-seitigen PDF: `d495a44921d25625c58dff812a65e99e2800a864b2876ab5abe13f2eca8d2975`
- Status des vorliegenden Repository-Artefakts: `SOURCE_CANONICALIZATION_PENDING_CI`

Der lokale Vorläufer wird durch seine Hashidentität referenziert. Diese
Repository-Fassung ist eine offen lesbare, deterministisch bau- und
maschinenprüfbare Kanonisierung desselben wissenschaftlichen Kerns. Sie wird
nicht als byteidentisch mit dem lokalen ZIP ausgegeben. Erst die CI erzeugt und
hashbindet ihre eigenen PDF-, Quell-, Beweis- und Veröffentlichungspakete.

## Mathematischer Kern

\[
\frac{\ell_{\mathrm P}}{t_{\mathrm P}}
=
\frac{E_{\mathrm P}}{p_{\mathrm P}}
=c,
\qquad
\ell_{\mathrm P}p_{\mathrm P}
=
t_{\mathrm P}E_{\mathrm P}
=\hbar,
\]

\[
\ell_{\mathrm P}
=
\frac{\hbar}{m_{\mathrm P}c}
=
\frac{Gm_{\mathrm P}}{c^2}.
\]

Die Lean-Formalisierung beweist diese Aussagen aus expliziten Definitionen und
Positivitätsvoraussetzungen. Sie beweist keine empirische Raumzeitdiskretheit,
keine bestimmte Quantengravitationsdynamik und keine Kosmogonie.

## Reproduktion

```sh
python3 tools/verify_wirkungsquadrat.py
cd formalization/Wirkungsquadrat_v1.0
lake update
lake build
```

Die GitHub-Workflows bauen zusätzlich das PDF, führen Axiom- und
Proof-Escape-Audits aus, erzeugen Hashbelege und halten die Zenodo-Publikation
bis zu einer expliziten, commitgebundenen Freigabe geschlossen.

## Lizenz

Artikel und nicht ausführbare Dokumentation: CC BY-NC-ND 4.0.  Neu erzeugter
Prüf- und Automatisierungscode: Apache-2.0, soweit die jeweilige Datei nichts
Abweichendes bestimmt.

Copyright 2026 Ingolf Lohmann.
