# Slack integration

## Purpose

This repository exposes a bounded, manually dispatched GitHub Actions workflow for sending a repository update to Slack:

- Workflow: `.github/workflows/qikvrt_slack_update.yml`
- Persisted work unit: `state/work_units/SLACK_UPDATES_TODO_2026-08-06.md`
- Secret name: `SLACK_WEBHOOK_URL`

## Safety boundary

The workflow is intentionally inert until the repository secret `SLACK_WEBHOOK_URL` is configured. It has no schedule, no `push` or `pull_request` trigger, and no embedded credential. A missing secret causes a fail-closed exit before any external request.

The workflow does not merge, publish, release, deploy, mutate Zenodo, submit to the IETF, or claim `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE`.

## Repository setup

An administrator must add a Slack incoming-webhook URL as the Actions secret `SLACK_WEBHOOK_URL` in the repository settings. Do not commit the webhook URL to Git.

After the secret exists, an authorized operator may run **QIK-VRT Slack update** from the Actions UI, supplying:

1. `summary`: the bounded update text to send.
2. `todo_path`: the repository path of the persisted to-do list; the default points to the work unit above.

## Operational status

- Repository adapter: present on this branch.
- Slack credential: not asserted by repository content.
- External dispatch: not performed by this change.
- Automatic schedule: absent.
- Repository-wide completion claims: absent.
