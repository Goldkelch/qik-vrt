# QIKVRT V2.13.4AU2 Productization Release Freeze Installer

Purpose: freeze the successful 4AU1 productization hardening run into public GitHub Releases for the Seed and Node repositories.

Start on Windows:

```text
START_HIER_RELEASE_FREEZE_INSTALL.cmd
```

Properties:

```text
ONE_COMMAND_WINDOWS_INSTALLER      YES
MASKED_TOKEN_INPUT                 YES
NO_POWERSHELL_PRIMARY_PATH          YES
NO_PS1_FILES                        YES
NO_GIT_COMMANDS_IN_INSTALLER        YES
NO_EMBEDDED_TOKEN                   YES
GITHUB_RELEASE_CREATE_OR_BLOCK      YES
RELEASE_FREEZE_EVIDENCE_UPLOAD      YES
```

Default targets:

```text
Seed: Goldkelch/qik-vrt @ main
Node: ingolf-lohmann/qik-vrt @ main
Seed tag: v2.13.4au1-seed-productization
Node tag: v2.13.4au1-node-productization
Reference public productization run: 4AU_20260708T170628Z_362577
```

The installer uploads release-freeze evidence files and creates GitHub Releases. It does not move existing tags. If a release/tag already exists, it blocks instead of silently rewriting history.
