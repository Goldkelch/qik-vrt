# V1.9 correction

V1.7 is BLOCK for owner-side execution because the GitHub `git/blobs` REST endpoint
returned `403 Resource not accessible by personal access token` in the field.

V1.9 correction:

- removed GitHub Git-Blobs REST write path,
- added Git CLI branch/tag push path,
- kept GitHub Release creation and release asset upload,
- added explicit token-permission failure messages,
- preserved PDF inclusion and GitHub-only Zenodo integration semantics.

Status: `V1_9_REPLACES_V1_7_FIELD_PERMISSION_BLOCK`.
