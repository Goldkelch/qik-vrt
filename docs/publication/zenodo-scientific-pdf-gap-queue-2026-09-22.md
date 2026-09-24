# Zenodo gap queue — scientific PDF corpus

Exact comparison subject: `Goldkelch/qik-vrt@ccedc24c9061ef03ec3bb77dfc47bc5d8928dd7d`

This queue is conservative. `NO_REPOSITORY_PUBLICATION_RECEIPT_ESTABLISHED` means that the repository publication index / receipt search does not establish a Zenodo publication for that exact PDF subject. It is not a global-absence claim about all Zenodo records.

## Already covered by repository Zenodo evidence — do not duplicate blindly

- EFFECT_ACK working-paper line — DOI `10.5281/zenodo.21498773`
- official status clarification — DOI `10.5281/zenodo.21500322`
- canonical temporal memory / EFFECT_ACK — DOI `10.5281/zenodo.21711193`
- Survival of the Anschlussfähigsten — DOI `10.5281/zenodo.21721918`
- observer-relative-retrocausality current synthesis — DOI `10.5281/zenodo.21947141`
- round-trip canonical publication — DOI `10.5281/zenodo.21888130`
- formalization / repository snapshots referenced by the publication index are separate published records and must be relation-bound, not recounted as new independent evidence.

## High-priority exact PDF subjects with no exact repository publication receipt established

| Path | Git blob | Disposition |
|---|---|---|
| `docs/publications/2026-07-21-mandelbrot-retrocausality/Mandelbrot_Anschlussordnung_Physik_Retrokausalitaet_V3_2026-07-21.pdf` | `e40b708706e9b94d1318fbb7ecfa1843561afa14` | NO_REPOSITORY_PUBLICATION_RECEIPT_ESTABLISHED |
| `docs/publications/2026-08-02-causality-is-relation-vrtcore/QIK-VRT_Kausalitaet_ist_Relation_VRTCore_2026-08-02.pdf` | `c75c6576b893a20dad37d8ba3f69800ba8887460` | repository_candidate |
| `docs/publications/2026-08-02-vrtcore-smg-h5/QIK-VRT_SMG_Fachartikel_DE_2026-08-02.pdf` | `e5587650dba77a8121fcfbba9c932d259477b23f` | candidate bundle explicitly lacks publication receipt |
| `docs/publications/2026-08-04-aphorism-corpus-scientific-assessment/QIK-VRT_Aphorism_Corpus_Scientific_Assessment_2026-08-04.pdf` | `05bb7bbe028f207c6b59d842cac8402bbfc3cca0` | candidate; human acoustic review pending |
| `docs/publications/2026-08-05-qik-vrt-quantum-causal-emergence/QIK-VRT_QCE_Fachartikel_DE_2026-08-05.pdf` | `17a3ac32fc6486e4b45a39ea16e3d6d65bea9691` | repository_candidate_open_correspondence |
| `documents/qikvrt_quantengravitation/QIKVRT_Fixpunktbeweis_final.pdf` | `c4c7cd8d8106cee0b5509b16398cbf71e04f32b5` | related repository DOI exists, but exact-PDF Zenodo publication not established by current index |
| `documents/qikvrt_quantengravitation/QIKVRT_Quantenkausalitaet_Quantengravitation_Vorlesung_Semester1.pdf` | `53bd3e5b60acd3f4b50d56c2b568b8915112b215` | NO_REPOSITORY_PUBLICATION_RECEIPT_ESTABLISHED |
| `documents/qikvrt_quantengravitation/quantengravitation_bekannte_mathematik_physik_semester2_v5.pdf` | `1ef56629602b19ebb1820edb0405bbf8e5ff0a97` | NO_REPOSITORY_PUBLICATION_RECEIPT_ESTABLISHED |
| `documents/qikvrt_quantengravitation/quantengravitation_semester3_abschluss_beweis_v3.pdf` | `850cb18fa5a82dd3d547bcd74847fc750899e3b2` | NO_REPOSITORY_PUBLICATION_RECEIPT_ESTABLISHED |
| `assets/pdf/odu_proof.pdf` | `8c0c0a0576ba5923790c0d60d5f98fcb3ebf34ee` | NO_REPOSITORY_PUBLICATION_RECEIPT_ESTABLISHED |

## Version-sensitive / do not publish until relation is resolved

- `QIK-VRT_Beobachterrelative_Retrokausalitaet_DE.pdf` and `QIK-VRT_Relationale_Zeit_und_wachsende_Evidenzkugel_DE.pdf`: a later current synthesis is already published under DOI `10.5281/zenodo.21947141`. These earlier/exact subjects require predecessor/version relation metadata rather than an unqualified new-record claim.
- `QIKVRT_Decision_Sufficiency_Delayed_Choice_Witness.pdf`: belongs to the same 2026-08-12 publication family; exact inclusion in the published v2 fileset must be checked before any new deposit.
- English arXiv staging PDF blob `62f66fc4f85d913a34b23edd5fa1a476db175b31`: staging/build duplicate; publication relationship must be resolved before Zenodo deposition.
- Monthly payload PDFs `a0076/a0078/a0079/a0081/a0582/a0584/a0586/a0587`: scientific-looking source mappings exist, but title/version/licence and overlap with the named quantum-gravity series must be resolved before deposition.

## Admission rule

A Zenodo upload may be claimed only after:
`exact bytes -> SHA-256 -> duplicate/version resolution -> owner/licence metadata -> machine proof -> authorized publish request -> Zenodo publication -> DOI -> public byte readback -> repository receipt`.

Archiving increases persistence/provenance. It does not turn project-authored documents into independent empirical confirmation.
