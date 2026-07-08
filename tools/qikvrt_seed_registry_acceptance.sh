#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Ingolf Lohmann.
set -eu
KNOWN="registry/KNOWN_NODE_REQUESTS.tsv"
CORE="/tmp/qikvrt_handshake_core"
if [ ! -x "$CORE" ]; then
  echo "QIKVRT_SEED_ACCEPTANCE BLOCK missing compiled core" >&2
  exit 80
fi
if [ ! -f "$KNOWN" ]; then
  echo "QIKVRT_SEED_ACCEPTANCE BLOCK missing KNOWN_NODE_REQUESTS.tsv" >&2
  exit 81
fi
mkdir -p registry/nodes evidence/seed_acceptance ledger tmp
while IFS='\t' read -r guid source_repo seed_repo request_url; do
  case "$guid" in ""|\#*) continue ;; esac
  echo "QIKVRT_SEED_ACCEPTANCE CHECK $guid $source_repo"
  curl -fsSL "$request_url" -o tmp/seed_registration_request.json
  "$CORE" seed "$guid" "$source_repo" "$seed_repo" tmp/seed_registration_request.json
  echo "QIKVRT_SEED_ACCEPTANCE PASS $guid"
done < "$KNOWN"
echo "QIKVRT_SEED_ACCEPTANCE_FINAL PASS"
