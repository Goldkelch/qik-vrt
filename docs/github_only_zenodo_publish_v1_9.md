# QIKVRT ODU V1.9 GitHub-only Zenodo release path

Status: `V1_9_GIT_CLI_GITHUB_RELEASE_FOR_ZENODO_INTEGRATION`.

V1.9 replaces the V1.7 GitHub Git-Data/Blob API path. The reported V1.7 error
`Resource not accessible by personal access token` occurred at the GitHub `git/blobs`
endpoint. V1.9 therefore uses Git CLI push plus GitHub Releases instead of the
Git-Blobs REST endpoint.

Required token permissions remain unavoidable:

- Fine-grained PAT: target repository selected, `Contents: Read and write`, `Metadata: Read`.
- Classic PAT: `repo` scope for private repositories, or suitable public repository write access.
- Organization-owned repositories may require owner-side approval of the PAT policy.

The script uses only `GITHUB_TOKEN`. It does not use a Zenodo token. Zenodo archival
requires that the target repository has been enabled in Zenodo's GitHub integration.

Execution files:

- `GITHUB_DRY_RUN_VERIFY_ONLY.cmd`
- `GITHUB_ZENODO_UPLOAD_AND_PUBLISH.cmd`
- `tools/github_zenodo_release_publish.ps1`

Publish result:

- creates/pushes a Git commit and tag,
- publishes a GitHub Release,
- uploads `assets/pdf/odu_proof.pdf` and `QIKVRT_ODU_V1_9_RELEASE_BUNDLE.zip` as release assets,
- Zenodo processes the release if the integration is active.

Boundary: a GitHub token that cannot write repository contents cannot publish a release-backed Zenodo artifact. No script can override GitHub permission policy.


## V1.9 release pre-check fix

A 404 response from GitHub release-by-tag lookup means the release does not exist yet. V1.9 treats that as expected absence and proceeds to create the release. Other API errors remain BLOCK.
