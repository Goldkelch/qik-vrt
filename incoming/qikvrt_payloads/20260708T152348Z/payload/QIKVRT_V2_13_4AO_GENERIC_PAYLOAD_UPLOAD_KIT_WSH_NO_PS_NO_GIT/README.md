<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
<!-- Copyright (c) 2026 Ingolf Lohmann. -->
# QIKVRT V2.13.4AO Generic Payload GitHub Upload Kit

This kit persists arbitrary payload files into an existing QIK-VRT GitHub node using the GitHub Contents API.

Windows primary path:

1. Put files/folders into `payload\`.
2. Double-click `START_HIER_QIKVRT_UPLOAD.cmd`.
3. Type `JA` or `YES` for copyright/license acceptance.
4. Type `JA` or `YES` for Product Owner upload authorization.
5. Choose `DRYRUN` first.
6. Choose `UPLOAD` and paste a fine-grained GitHub token only when the dry run is correct.

No Git is used. No `.ps1` is executed. No token is embedded.
