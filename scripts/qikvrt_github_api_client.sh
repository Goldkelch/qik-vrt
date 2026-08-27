#!/bin/sh
set -eu
OWNER="${1:?owner}"
REPO="${2:?repo}"
PAYLOAD_FILE="${3:?payload file}"
TOKEN="${GITHUB_TOKEN:?GITHUB_TOKEN required in owner-controlled runtime}"
REQUEST_ID="${4:?stable request id}"
QIKVRT_API_TOKEN="$TOKEN" python3 scripts/qikvrt_api_client.py \
  --base-url https://api.github.com \
  --owner "$OWNER" \
  --repo "$REPO" \
  --dispatch-kind repository \
  --payload-file "$PAYLOAD_FILE" \
  --dry-run true \
  --request-id "$REQUEST_ID"
