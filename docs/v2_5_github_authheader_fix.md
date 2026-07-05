# QIKVRT ODU V2.5 GitHub transport authentication fix

V2.3 is BLOCK because GitHub Git transport returned `remote: invalid credentials`.

Root cause: Git transport authentication must not rely on stale Windows Credential Manager state or a Bearer-style Git extraHeader. V2.5 uses a Basic HTTPS Authorization extraHeader generated from the owner-supplied GitHub PAT as `x-access-token:<token>`, disables credential helper for the publish commands, and runs a non-mutating `git ls-remote` authentication preflight before any branch push, tag push, GitHub Release creation, or asset upload.

No Zenodo API token is used. Zenodo publication remains owner-side through the enabled Zenodo-GitHub integration after GitHub Release publication.
