# QIKVRT Self-Contained GitHub Repository with REST/TCP-IP API V1

Created: 2026-06-26 05:43:26 CEST

This repository is a self-contained QIK-VRT repository root. It includes:

```text
GitHub-compatible REST/TCP-IP API shim
GitHub Actions workflow_dispatch / repository_dispatch workflow
OpenAPI contract
Handler implementation
Client implementation
Unit and TCP/IP E2E tests
CI workflow
Metagrammar test inventory
Audit and uploadability gates
```

## Local TCP/IP API

```bash
make run-api
```

Health:

```bash
curl http://127.0.0.1:8766/health
```

## Tests

```bash
make test
```

## GitHub REST API enablement

After upload to GitHub, the repository can be triggered through GitHub REST:

```text
POST https://api.github.com/repos/{owner}/{repo}/actions/workflows/qikvrt_mesh_api.yml/dispatches
POST https://api.github.com/repos/{owner}/{repo}/dispatches
```

## Boundaries

```text
FIXED_RELEASE_COMMIT = a8a9cb2666a91411489d4fc90a5306908f8428ea
FIXED_RELEASE_TREE = c5cefebd20b5836d730a4e9da82eeaa5c9363ebf
LIVE_GITHUB_ACTIONS_RUN = SUCCESS (run 29764193906)
GITHUB_PAGES_BUILD_AND_DEPLOY = SUCCESS (run 29764192834)
ZENODO_DOI_FOR_EXACT_RELEASE = OPEN
INDEPENDENT_THIRD_PARTY_REPRODUCTION = OPEN
```

These hosted results establish the named GitHub effects only. They do not
establish non-bypassability in every integration, production hardening,
external adoption, or empirical validation of claims outside the executable
software boundary.
