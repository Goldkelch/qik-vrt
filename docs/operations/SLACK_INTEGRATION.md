# Slack integration

## Purpose

This repository provides a bounded GitHub Actions adapter for Slack:

- Workflow: `.github/workflows/qikvrt_slack_update.yml`
- Reviewed authorization: `state/authorization/slack/SLACK_UPDATE_DISPATCH_2026-08-06_V1.json`
- Persisted update and to-do list: `state/work_units/SLACK_UPDATES_TODO_2026-08-06.md`

The adapter reuses existing workspace-authorized Slack credentials. Credential values remain GitHub Actions secrets and are never committed, printed, uploaded, or returned by the workflow.

## Supported credential bindings

The adapter checks the following non-exported bindings in order.

### Incoming webhook

1. `SLACK_WEBHOOK_URL`
2. `QIKVRT_SLACK_WEBHOOK_URL`
3. `SLACK_INCOMING_WEBHOOK_URL`

The selected value must use an approved Slack incoming-webhook origin.

### Slack Web API

Bot token:

1. `SLACK_BOT_TOKEN`
2. `QIKVRT_SLACK_BOT_TOKEN`
3. `SLACK_API_TOKEN`

Channel or conversation ID:

1. `SLACK_CHANNEL_ID`
2. `QIKVRT_SLACK_CHANNEL_ID`
3. `SLACK_CHANNEL`

The API fallback requires a bot token and an explicit channel or conversation ID. A missing, partial, or malformed binding fails closed before any external request.

## Execution boundary

### Pull requests and candidate-branch pushes

The `credential-probe` job checks only whether a supported, non-exported credential binding is present. It performs no network request and does not reveal secret content. The explicit candidate-branch push trigger exists so the Mirror repository can run the same probe even when a newly introduced pull-request workflow is not scheduled there.

### Initial Authority promotion

When the reviewed authorization is introduced on `Goldkelch/qik-vrt` `main` for the first time, the workflow may post exactly one bounded update. It verifies that the authorization file did not exist in the pre-push commit and that the request, repository, credential policy, and payload source match the reviewed contract.

The identical Mirror workflow does not automatically post when introduced on Mirror `main`, preventing a duplicate effect.

### Future manual posts

`workflow_dispatch` remains available. It requires:

- the exact stable `request_id`;
- `effect_accepted=true`;
- the reviewed authorization file;
- the persisted payload source;
- either a supported incoming webhook or a supported bot-token/channel pair.

## Evidence

A successful dispatch creates an artifact containing:

- the request ID;
- repository, commit, workflow run, and payload SHA-256 bindings;
- the observed Slack transport method and acknowledgement;
- Slack channel and message timestamp when returned by `chat.postMessage`;
- explicit non-claims for `PASS`, `FINAL_PASS`, and `EFFECT_ACK_DONE`.

The receipt never contains the webhook URL, bearer token, or another credential.

## Current state

- Adapter candidate: persisted on the paired review branches.
- Authority incoming-webhook-only probe run `31053142194`: no supported webhook binding observed; no network request occurred.
- Dual-transport credential probes: pending on the exact successor heads.
- External Slack dispatch: not yet performed.
- Repository-wide completion claims: absent.
