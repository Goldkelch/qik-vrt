<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Repository-owned GitHub publication runtime

GitHub publication readiness is part of the repository, not an assumption
about a particular workstation, runner image, or AI session. The repository
locks GitHub CLI 2.96.0 for all supported platforms, verifies downloaded bytes,
checks authentication and repository permission before an effect journal is
prepared, binds Git transport to the exact CLI through repository-local Git
configuration, and emits a redacted machine receipt.

Credentials are the one deliberate external capability. The repository cannot
create an identity or permission for itself. A caller may supply `GH_TOKEN`,
`GITHUB_TOKEN`, a secure `gh auth login` store, the ephemeral GitHub Actions
token, or a connected GitHub App. Token values are never committed, cached,
written to receipts, or printed by the runtime.

## Deterministic entrypoints

Validate the checked-in capability without network or credentials:

```sh
python3 -B tools/qikvrt_github_publish_runtime.py offline-check --json
```

Install the checksum-locked CLI when absent, verify the selected repository,
identity, push permission, base head and Git transport, and configure a
secret-free repository-local credential helper:

```sh
python3 -B tools/qikvrt_github_publish_runtime.py prepare \
  --repository Goldkelch/qik-vrt \
  --remote origin \
  --base main \
  --install --accept-third-party \
  --configure-local-git --require-clean --json
```

When the receipt state is `CREDENTIAL_REQUIRED`, establish caller-owned secure
authentication and rerun the same prepare command:

```sh
python3 -B tools/qikvrt_github_publish_runtime.py login \
  --install --accept-third-party
```

Non-interactive callers should set `GH_TOKEN` or `GITHUB_TOKEN` only in their
process/job environment. Do not place a token in a remote URL, command line,
repository file, build cache, artifact, or receipt.

Run a GitHub CLI command through the exact repository-locked executable:

```sh
python3 -B tools/qikvrt_github_publish_runtime.py gh -- \
  pr create --draft --repo Goldkelch/qik-vrt --base main \
  --head agent/example --title "Example" --body-file /path/to/body.md
```

The `prepare` command is effect-free with respect to GitHub. With explicit
flags it may install the verified local tool cache, update `.git/config` with a
secret-free helper command, and write the ignored mode-0600 receipt under
`.qikvrt/evidence`. It does not push, create a pull request, merge, release,
deploy, or mutate Zenodo, DOI, IETF, Authority, or Mirror state.

## CI and transport independence

`.github/workflows/qikvrt_github_publish_runtime.yml` continuously validates
the offline contract. Its manually dispatched authenticated job receives only
a job-scoped GitHub token, installs/verifies the same exact CLI, runs the same
effect-free prepare path, and retains no credential artifact.

Local CLI, GitHub Actions, and a connected GitHub App are interchangeable
transport lanes with the same repository-owned preflight and receipt meaning.
The connected app remains session-owned and must not export its credential to
the repository. If one lane is unavailable, another lane may upload the exact
candidate and open the draft review object without weakening the integration
order.

Independent candidate branches may be prepared and verified in parallel. They
hold no remote writer lease while waiting for credentials or review. Authority
promotion remains one expected-head-bound serial lane; Mirror work starts only
after Authority promotion. A blocked candidate therefore cannot stall an
unrelated conflict component.

## Publication boundary

The ordinary output is an Authority draft pull request. The branch head, draft
pull-request head, and selected Authority base must be reobserved after the
effect. A ready receipt is neither authorization nor proof of publication.
Merge, force-push, release, deployment, Zenodo/DOI/IETF mutation, Mirror port,
and Mirror promotion remain separately authorized effects.
