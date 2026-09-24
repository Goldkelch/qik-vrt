# Scientific PDF corpus inventory — QIK-VRT

Exact repository subject: `Goldkelch/qik-vrt@ccedc24c9061ef03ec3bb77dfc47bc5d8928dd7d`  
Tree scan: recursive, complete (`truncated=false`)  
PDF paths found: 34.

## Evidence rule

This corpus enlarges the **documentary and claim graph**, not automatically the independent empirical evidence. A PDF authored within the same project can establish provenance, chronology, definitions, formal arguments and prior-art continuity. It does **not** become independent experimental confirmation merely by being archived or assigned a DOI.

Each Zenodo deposit must therefore preserve:
- immutable source path and Git blob identity;
- title/version/date/author metadata;
- relation to predecessor/successor documents;
- evidence class: FORMAL / REPOSITORY / LITERATURE-SYNTHESIS / INTERPRETATIVE / OPEN;
- explicit non-implications and falsifiers;
- duplicate detection before upload.

## Scientific/publication candidates

### Publication series
- `docs/publications/2026-07-21-mandelbrot-retrocausality/Mandelbrot_Anschlussordnung_Physik_Retrokausalitaet_V3_2026-07-21.pdf` — blob `e40b708706e9b94d1318fbb7ecfa1843561afa14`
- `docs/publications/2026-07-22-effect-ack-universal-effect-control/QIK-VRT_EFFECT_ACK_Universalisierbare_Wirkungssteuerung_2026-07-22.pdf` — `ba8d79437709bdf835e29903bd1d2918308d70cb`
- `docs/publications/2026-07-22-qik-vrt-status-clarification/QIK-VRT_EFFECT_ACK_Statusklaerung_2026-07-22.pdf` — `e093ae7980426648822853815ee7d6132ada2346`
- `docs/publications/2026-07-30-canonical-temporal-memory-effect-ack/QIK-VRT_Kanonischer_Speicher_Retrokausalitaet_EFFECT_ACK_2026-07-30.pdf` — `8e37543ecea0e3e44e55347fc007dafff0f0a381`
- `docs/publications/2026-07-31-survival-anschlussfaehigsten/Survival_der_Anschlussfaehigsten_2026-07-31.pdf` — `1b0f15403fe95e46d17ffe54d7b3ea8ef3402452`
- `docs/publications/2026-08-02-causality-is-relation-vrtcore/QIK-VRT_Kausalitaet_ist_Relation_VRTCore_2026-08-02.pdf` — `c75c6576b893a20dad37d8ba3f69800ba8887460`
- `docs/publications/2026-08-02-vrtcore-smg-h5/QIK-VRT_SMG_Fachartikel_DE_2026-08-02.pdf` — `e5587650dba77a8121fcfbba9c932d259477b23f`
- `docs/publications/2026-08-04-aphorism-corpus-scientific-assessment/QIK-VRT_Aphorism_Corpus_Scientific_Assessment_2026-08-04.pdf` — `05bb7bbe028f207c6b59d842cac8402bbfc3cca0`
- `docs/publications/2026-08-05-qik-vrt-quantum-causal-emergence/QIK-VRT_QCE_Fachartikel_DE_2026-08-05.pdf` — `17a3ac32fc6486e4b45a39ea16e3d6d65bea9691`
- `docs/publications/2026-08-12-observer-relative-retrocausality/QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.pdf` — `858f4049736692c8fd46d54f658d2ac888c1488c`
- `docs/publications/2026-08-12-observer-relative-retrocausality/QIK-VRT_Relationale_Zeit_und_wachsende_Evidenzkugel_DE.pdf` — `44aeb01177d0f830fdf18ca82278d055b09b2c56`
- `docs/publications/2026-08-12-observer-relative-retrocausality/QIKVRT_Decision_Sufficiency_Delayed_Choice_Witness.pdf` — `53de5657a99b195625b6348387f2804c8155430f`

### Quantum-gravity / formal proof series
- `documents/qikvrt_quantengravitation/QIKVRT_Fixpunktbeweis_final.pdf` — `c4c7cd8d8106cee0b5509b16398cbf71e04f32b5`
- `documents/qikvrt_quantengravitation/QIKVRT_Quantenkausalitaet_Quantengravitation_Vorlesung_Semester1.pdf` — `53bd3e5b60acd3f4b50d56c2b568b8915112b215`
- `documents/qikvrt_quantengravitation/quantengravitation_bekannte_mathematik_physik_semester2_v5.pdf` — `1ef56629602b19ebb1820edb0405bbf8e5ff0a97`
- `documents/qikvrt_quantengravitation/quantengravitation_semester3_abschluss_beweis_v3.pdf` — `850cb18fa5a82dd3d547bcd74847fc750899e3b2`
- `assets/pdf/odu_proof.pdf` — `8c0c0a0576ba5923790c0d60d5f98fcb3ebf34ee`

### Staging / English synthesis
- `publication-staging/arxiv-observer-relative-retrocausality-en-v2/main.pdf` — `62f66fc4f85d913a34b23edd5fa1a476db175b31`
- `release/observer-relative-retrocausality-current-synthesis-zenodo-v2/original-candidate-47510c8/QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.pdf` — `bb37e1ce0e79e6aae16afced515e7d7b5f11b492`

### Monthly scientific payloads requiring metadata/content verification before deposit
- `a0076.pdf` — mapped as quantengravitation semester2 beweisskript v4
- `a0078.pdf`, `a0079.pdf` — mapped as quantenkausalitaet/rechnerarchitektur semester material
- `a0081.pdf` — mapped as semester2 script
- `a0582.pdf` — mapped as quantengravitation/bekannte Mathematik/Physik semester material
- `a0584.pdf`, `a0586.pdf`, `a0587.pdf` — mapped as quantengravitation semester3 Abschluss/Beweis versions

## Exact duplicates that must not become separate evidentiary claims

The recursive scan found repeated Git blobs in different paths:
- Mandelbrot PDF: `e40b708...` also under `formalization/.../source/`.
- ODU proof: `8c0c0a0...` also under `incoming/.../Evidences/`.
- Four quantum-gravity PDFs under `documents/` are repeated under `incoming/.../Evidences/`.
- arXiv English `main.pdf`: blob `62f66fc...` occurs in both staging root and `build/`.

Zenodo staging must deduplicate byte-identical blobs and represent path aliases as provenance, not independent evidence.

## Publication admission

A candidate may enter the Zenodo publication queue only after:
1. bytes are read and cryptographically fingerprinted;
2. authorship/licence/publication status are checked;
3. duplicates/versions are resolved;
4. scientific claims are typed and linked to their actual support;
5. the deposit metadata names the exact repository subject;
6. publication is followed by DOI and public-byte readback.

Until step 6: `ZENODO_PUBLISHED = FALSE`.
