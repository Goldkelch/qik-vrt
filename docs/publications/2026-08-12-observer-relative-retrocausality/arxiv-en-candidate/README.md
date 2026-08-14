<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# English arXiv candidate — repository source copy

Status: **`LOCAL_STAGING_NOT_SUBMITTED`**.

This directory gives the English QIK-VRT manuscript a repository-visible,
reviewable source path. It is a local pre-submission copy only. It does not
mean that arXiv has received, accepted, announced, endorsed, or assigned an
identifier to this manuscript.

## Contents and deliberate omissions

| Path | Role |
|---|---|
| `main.tex` | Byte-exact English LaTeX source from the frozen staging candidate. |
| `STAGING_README.md` | Byte-exact staging README, retained under its original content binding. |
| `arxiv_submission_manifest.json` | Byte-exact staging manifest; its status is `LOCAL_STAGING_NOT_SUBMITTED`. |
| `REPOSITORY_COPY_PROVENANCE.json` | Explains this later local repository copy and binds the retained bytes. |
| `SHA256SUMS` | Fixity index for every file in this directory except itself. |

The deliberately omitted files are the rendered candidate PDF,
`arxiv-source.tar.gz`, the rendering receipt, and the action-time
authorization form. Keeping those upload-oriented bytes outside this repository
copy prevents a repository source path from being mistaken for an already
authorized external submission.

## Status and claim boundary

The manuscript names Ingolf Lohmann as author and attributes the QIK-VRT
research programme, operational terminology, and correspondence thesis to him.
It distinguishes its finite formal/executable result from independent empirical
confirmation and scientific consensus. It does not claim backward-running
proper time, reception before emission, past overwrite, causal loops,
superluminal signalling, a controllable message to the past, or an arXiv/IETF
publication.

The text itself contains immutable source references to the Authority and
Mirror GitHub snapshots and to the retained Zenodo material. This local source
copy adds a stable repository path for review; a public GitHub URL can be
formed only after a separately authorized Git commit and remote publication.

## Later submission boundary

Any future arXiv action must freeze the then-intended upload archive and
destination metadata, bind them to a new author decision, verify the account
and license fields in the arXiv interface, and obtain an action-time
confirmation. This directory does not grant that authority.
