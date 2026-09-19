# Historical V45 launchers

This directory contains the preserved QIK-VRT V45 Windows command launchers
that previously occupied repository root.

The migration is structural only:

- each `.cmd` file keeps its original Git blob identity;
- no launcher semantics are changed by the move;
- these files are historical compatibility material, not canonical entry points;
- the canonical current launcher remains `qikvrt.py` with maintained wrappers;
- the legacy root-level `SHA256SUMS` file remains a historical V45.20
  snapshot and is intentionally not rewritten as current integrity authority.

Current repository integrity is defined by
`REPOSITORY_FILE_MANIFEST.json`, `SHA256SUMS.txt`, and
`REPOSITORY_FILE_MANIFEST.json.sha256`.
