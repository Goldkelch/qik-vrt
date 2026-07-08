# QIK-VRT V2.13.4AU1 Productization Hardening Audit Pushfix Installer

Start on Windows:

```text
START_HIER_PRODUCTIZATION_HARDENING_INSTALL.cmd
```

This package supersedes 4AU when the Seed Mesh Audit Export run evidence does not appear. It keeps the 4AU one-command hidden-token installer and adds robust GitHub Actions commit/push retry logic for workflow-generated outputs.

Key fixes:

```text
SEED_AUDIT_RUN_EVIDENCE_TIMEOUT_AFTER_4AU = FIXED
WORKFLOW_OUTPUT_PUSH_RACE = MITIGATED
AUDIT_REPORT_DOC_OUTPUT = ADDED
MASKED_TOKEN_INPUT = RETAINED
NO_PS1 = PASS
NO_POWERSHELL_PRIMARY_PATH = PASS
NO_GIT_IN_WINDOWS_INSTALLER = PASS
```

Run in UPLOAD mode, dispatch workflows, then verify the run-id scoped audit evidence and dashboard outputs.
