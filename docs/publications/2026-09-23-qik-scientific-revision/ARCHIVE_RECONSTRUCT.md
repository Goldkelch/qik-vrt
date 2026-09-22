# Exact-DOCX reconstruction

The repository carries two views of each artifact:

1. a diff-friendly Markdown rendering for review and indexing;
2. an exact-byte DOCX archive encoded as ordered Base64 parts.

Reconstruct on a POSIX shell from this publication directory:

```sh
cat archive/QIK_Publikationsfassung_revidiert.docx.b64.part-* | base64 -d > QIK_Publikationsfassung_revidiert.docx
cat archive/QIK_Wissenschaftlicher_Revisionsbericht.docx.b64.part-* | base64 -d > QIK_Wissenschaftlicher_Revisionsbericht.docx
sha256sum -c SHA256SUMS
```

Expected SHA-256 values:

- `QIK_Publikationsfassung_revidiert.docx`: `1c70cbe19edd5a34dc764ad6527cf14761b78b85bc4a157d8aed3f5853b8a020`
- `QIK_Wissenschaftlicher_Revisionsbericht.docx`: `e4be998ce2ef43f0575fa91b2974d72325f8bf820a72410cfbf697e38fc03bb1`

This encoding is archival transport only; the decoded DOCX bytes are the identity-bearing artifacts.
