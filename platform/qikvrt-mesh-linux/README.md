<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# qikvrt-meshd proof appliance

This directory contains the POSIX C process used by the V1 OCI proof runtime.
It is an application on a host-supplied Linux kernel, not a kernel, root
distribution, complete Internet stack, SNMP implementation or effect executor.

Build and test through `make mesh-linux-proof-test`.  Generate the OCI layout
and Docker-load archive through `tools/qikvrt_mesh_linux_oci.py`; no container
engine or network fetch is required.
