<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Zenodo-v2-Hüllennachweis — keine Änderung der H5/H6-Originalbytes

Publication ID: `qikvrt-vrtcore-virtual-sphere-h6-v1`

`content_changed=false`: Die bereits im Commit `c5d4a3b5ae10cf72845b1839c6075cdd2711f315` enthaltenen
H5/H6-Source-Candidate-Bytes werden nicht umgeschrieben. Diese Aussage bezieht
sich nur auf jene unveränderten Sourcebytes, nicht auf die neue Prüfhülle. Neu
ist ausschließlich eine additive Zenodo-v2-Prüfhülle mit Claim-Projektion, Return-Receipt,
Grenztestbericht, Metadaten und maschinenlesbarem Proof-Bundle.

Die lokalen Formalgruppen `H6-C01, H6-C02, H6-C03, H6-C04, H6-C05, H6-C06` werden als `FORMAL_PROVED` projiziert. Ihre
Theoremreferenzen stammen ausschließlich aus der exakten lokalen Kernel-Receipt
und deren Axiom-Inventar. Der terminale Push-Run `30747218720` führt die
H5/H6-Prüfung am exakten Commit `c5d4a3b5ae10cf72845b1839c6075cdd2711f315` gehostet und automatisiert
erneut aus. Sein Log ist weder unabhängiges Peer-Review noch Ersatz für den
formalen Beweis.

Wo der ursprüngliche Source-Claim weiter reicht als die exakt gebundenen
Theorem- oder Laufreferenzen, enthält die v2-Projektion ausdrücklich eine
konservative Teilbehauptung; die ursprünglichen Source-Bytes bleiben unverändert.

Zenodo-Version und Upload-Typ folgen der unveränderten `CITATION.cff`: H5 wird
als Artikel/Working Paper abgebildet, H6 als Software ohne Publication-Subtype.

Sichtbare Source→Projection-Aufspaltung:

- `H6-C07` → enger `EMPIRICALLY_EVIDENCED`-Teil für den konkreten receipt-gebundenen lokalen Lauf plus `H6-C07-RESIDUAL` als `OPEN` für die nicht aus Einzelruns ableitbare Universalform.

Physische Schließung, eine physische Vereinigung der Gravitation mit dem
Standardmodell, ein Graviton-Nachweis und die Identität einer virtuellen
Kosmogenese mit dem physischen Urknall bleiben ausdrücklich `OPEN` bzw.
`NOT_CLAIMED`.

Keine `OWNER_ZENODO_AUTHORIZATION`, kein `publish-request.json`, kein Workflow
und keine externe Mutation sind Bestandteil dieses Kandidaten.
