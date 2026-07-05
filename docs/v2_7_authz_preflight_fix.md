# QIKVRT V2.7 AuthZ Preflight Fix

V2.6 reached GitHub transport and local commit, but failed at `git push` because the authenticated GitHub identity did not have write permission on the target repository. The observed owner-side log showed: `Permission to ingolf-lohmann/qik-vrt.git denied to Goldkelch`.

V2.7 moves this condition into an early REST authorization preflight before bundle creation, worktree creation, commit, tag, push or release. The script now obtains the authenticated GitHub login via `/user`, reads the repository `permissions` object via `/repos/{owner}/{repo}`, and requires `admin`, `maintain` or `push` before any mutating Git operation.

Allowed remedies:

1. Use a token from an account that can write to the target repository.
2. Grant the authenticated account Write/Maintain/Admin access on the target repository.
3. Change `GITHUB_OWNER` to the repository actually owned by the authenticated account and enabled in Zenodo GitHub integration.

No Zenodo token is introduced. The workflow remains GitHub Release -> Zenodo GitHub integration.
