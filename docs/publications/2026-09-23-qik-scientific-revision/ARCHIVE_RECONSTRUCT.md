# Exact-DOCX reconstruction

The repository carries two reviewable Markdown representations and an exact-byte ZIP archive encoded as ordered Base64 parts.

From this publication directory:

```sh
cat archive/QIK_scientific_revision_exact_artifacts.zip.b64.part-* \
  | base64 -d > QIK_scientific_revision_exact_artifacts.zip
printf '%s  %s\n' \
  a83d7b10db2065735ac033d39092f13d8f38ab311d6e1a3080236e473b51f02a \
  QIK_scientific_revision_exact_artifacts.zip | sha256sum -c -
unzip -o QIK_scientific_revision_exact_artifacts.zip
sha256sum -c SHA256SUMS
```

Expected byte identities:

- archive ZIP: `a83d7b10db2065735ac033d39092f13d8f38ab311d6e1a3080236e473b51f02a`
- `QIK_Publikationsfassung_revidiert.docx`: `1c70cbe19edd5a34dc764ad6527cf14761b78b85bc4a157d8aed3f5853b8a020`
- `QIK_Wissenschaftlicher_Revisionsbericht.docx`: `e4be998ce2ef43f0575fa91b2974d72325f8bf820a72410cfbf697e38fc03bb1`

The Base64 files are transport encoding only. The decoded ZIP and the two extracted DOCX files carry the byte identities used for the Zenodo publication gate.
