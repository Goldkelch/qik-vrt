# QIK-VRT Mesh Notes — monotone Evidenzkugel

**Stand:** 2026-09-25  
**Modus:** append-only / monotonic

## Grundregel

Der persistierte Zenodo-Kern bleibt unverändert als Provenienz- und Publikationsanker bestehen. Neue Anschlussfähigkeit wächst ausschließlich durch additive Knoten und Kanten.

`OLD_NODES ⊆ NEW_NODES`  
`OLD_EDGES ⊆ NEW_EDGES`  
`PREDECESSOR_EVIDENCE_TRANSFER = FALSE`

Korrekturen löschen keine historische Evidenz. Sie werden als neue `supersedes`-, `refines`- oder `contradicts`-Kanten ergänzt. Eine externe Referenz ist weder Zustimmung noch Beweisübernahme.

## Zenodo-Kern

Repository-verifizierter Snapshot: `release/zenodo-corpus-proof-2026-07-28/canonical-union/CANONICAL_UNION_CORPUS.json`  
Canonical-union SHA-256: `092c52cbfba8defd7a7136d7fa2b4848fa2e41416d4b85654a6cb8d5fcd953f7`

- 24 Record-Identitäten
- 12 Concept-Linien
- 19 Payload-Cluster

Die 12 Concept-Linien:
- [10.5281/zenodo.20712300](https://doi.org/10.5281/zenodo.20712300) → Records: [20712301](https://doi.org/10.5281/zenodo.20712301)
- [10.5281/zenodo.21244411](https://doi.org/10.5281/zenodo.21244411) → Records: [21244412](https://doi.org/10.5281/zenodo.21244412), [21245282](https://doi.org/10.5281/zenodo.21245282), [21245951](https://doi.org/10.5281/zenodo.21245951), [21247297](https://doi.org/10.5281/zenodo.21247297), [21247388](https://doi.org/10.5281/zenodo.21247388), [21252415](https://doi.org/10.5281/zenodo.21252415), [21252649](https://doi.org/10.5281/zenodo.21252649), [21266670](https://doi.org/10.5281/zenodo.21266670), [21267021](https://doi.org/10.5281/zenodo.21267021)
- [10.5281/zenodo.21482022](https://doi.org/10.5281/zenodo.21482022) → Records: [21482023](https://doi.org/10.5281/zenodo.21482023)
- [10.5281/zenodo.21488115](https://doi.org/10.5281/zenodo.21488115) → Records: [21488116](https://doi.org/10.5281/zenodo.21488116), [21498774](https://doi.org/10.5281/zenodo.21498774), [21501365](https://doi.org/10.5281/zenodo.21501365), [21518464](https://doi.org/10.5281/zenodo.21518464), [21529081](https://doi.org/10.5281/zenodo.21529081)
- [10.5281/zenodo.21498772](https://doi.org/10.5281/zenodo.21498772) → Records: [21498773](https://doi.org/10.5281/zenodo.21498773)
- [10.5281/zenodo.21500321](https://doi.org/10.5281/zenodo.21500321) → Records: [21500322](https://doi.org/10.5281/zenodo.21500322)
- [10.5281/zenodo.21515073](https://doi.org/10.5281/zenodo.21515073) → Records: [21515074](https://doi.org/10.5281/zenodo.21515074)
- [10.5281/zenodo.21582780](https://doi.org/10.5281/zenodo.21582780) → Records: [21582781](https://doi.org/10.5281/zenodo.21582781)
- [10.5281/zenodo.21633410](https://doi.org/10.5281/zenodo.21633410) → Records: [21633411](https://doi.org/10.5281/zenodo.21633411)
- [10.5281/zenodo.21636773](https://doi.org/10.5281/zenodo.21636773) → Records: [21636774](https://doi.org/10.5281/zenodo.21636774)
- [10.5281/zenodo.21640159](https://doi.org/10.5281/zenodo.21640159) → Records: [21640160](https://doi.org/10.5281/zenodo.21640160)
- [10.5281/zenodo.21640172](https://doi.org/10.5281/zenodo.21640172) → Records: [21640173](https://doi.org/10.5281/zenodo.21640173)

Der vollständige maschinenlesbare Satz aller 24 Records und Kanten steht in `QIKVRT_MESH_EVIDENCE_SPHERE_MONOTONIC_V1.json`.

**Beobachtungsgrenze:** Die direkte Zenodo-Web/API-Neuabfrage war aus dieser Ausführungsumgebung nicht erreichbar. Deshalb werden hier keine neueren Zenodo-Records behauptet; der Seed stammt aus dem bereits repository-verifizierten öffentlichen Snapshot.

## Externe GitHub-Anschlussknoten

- `ATTESTATION_CHAIN` — [in-toto/in-toto ](https://github.com/in-toto/in-toto): Signed layouts and link metadata for verifiable step/material/product chains.
- `PROVENANCE_MODEL` — [slsa-framework/slsa ](https://github.com/slsa-framework/slsa): Build provenance model for where, when and how artifacts were produced.
- `PROVENANCE_VERIFICATION` — [slsa-framework/slsa-verifier ](https://github.com/slsa-framework/slsa-verifier): Verifier for SLSA provenance and source/build bindings.
- `TRANSPARENCY_LOG` — [sigstore/rekor ](https://github.com/sigstore/rekor): Append-only transparency log for signed software-supply-chain metadata.
- `ARTIFACT_SIGNATURE` — [sigstore/cosign ](https://github.com/sigstore/cosign): Signing and verification of OCI and other artifacts with Sigstore.
- `UPDATE_TRUST` — [theupdateframework/python-tuf ](https://github.com/theupdateframework/python-tuf): Reference implementation of TUF secure update metadata and trust rotation.
- `SBOM_MODEL` — [spdx/spdx-spec ](https://github.com/spdx/spdx-spec): Open SBOM and system/component metadata standard.
- `BOM_ATTESTATION_MODEL` — [cyclonedx/specification ](https://github.com/CycloneDX/specification): BOM/attestation model covering software, hardware, AI/ML and related domains.
- `EVIDENCE_GRAPH` — [guacsec/guac ](https://github.com/guacsec/guac): Aggregates software security metadata into a normalized high-fidelity graph.
- `OCI_ARTIFACT_TRANSPORT` — [oras-project/oras ](https://github.com/oras-project/oras): OCI registry transport for artifacts, images and packages.
- `SBOM_EXTRACTION` — [anchore/syft ](https://github.com/anchore/syft): Generates SBOMs from images/filesystems and supports SPDX/CycloneDX/in-toto outputs.

## Anschlusssemantik

Ein externer Knoten darf erst dann zu QIK-VRT-Evidenz werden, wenn eine konkrete, frische Bindung materialisiert ist, z. B. über:

`TARGET_IDENTITY ∧ VERSION/COMMIT ∧ HASH/ATTESTATION ∧ RELATION_TYPE ∧ FRESH_READBACK`

Bis dahin gilt:

`REFERENCE_LINK ≠ EVIDENCE_TRANSFER ≠ EFFECT_ACK`

Die Evidenzkugel wächst damit monoton, ohne ihre historischen Zustände umzuschreiben.
