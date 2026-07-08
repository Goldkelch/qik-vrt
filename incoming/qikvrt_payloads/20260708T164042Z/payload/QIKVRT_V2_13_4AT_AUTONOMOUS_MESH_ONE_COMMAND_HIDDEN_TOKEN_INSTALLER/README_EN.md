# QIKVRT V2.13.4AT Autonomous Seed/Node Mesh Maintenance Installer

This package replaces the visible token prompt with a masked local Windows password dialog and adds the missing autonomous Seed/Node mesh maintenance flows.

Start:

```text
START_HIER_AUTONOMOUS_MESH_INSTALL.cmd
```

The installer asks interactively for license acceptance, Product Owner authorization, Seed/Node repositories, branches, DRYRUN or UPLOAD, masked repository-specific tokens, final UPLOAD confirmation, and optional sequenced workflow dispatch.

New autonomous flows:

1. Node publishes heartbeat.
2. Seed accepts the known node request.
3. Seed creates `registry/NODEMESH_INDEX.json`.
4. Seed creates `registry/NODEMESH_STATUS.json`.
5. Node reads the Seed index and acknowledges Seed acceptance.
6. Both repositories persist evidence.

Boundaries: no PowerShell primary path, no `.ps1`, no Git in the Windows installer, no embedded token, no visible token in console logs, no foreign repository mutation, no global scanning, no self propagation.
