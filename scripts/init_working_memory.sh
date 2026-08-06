#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

set -eu

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/init_working_memory.sh \
    --mode={proofs|experiments|production} \
    --runtime={python|lean4|docker|cli} \
    --backup={local|github|zenodo}

Prints a non-secret .env template to standard output.
Performs no network access and no repository or external mutation.
USAGE
}

fail() {
  printf 'QIKVRT_WORKING_MEMORY_BLOCK: %s\n' "$1" >&2
  usage >&2
  exit 2
}

mode=''
runtime=''
backup=''

while [ "$#" -gt 0 ]; do
  case "$1" in
    --mode=*) mode=${1#--mode=} ;;
    --runtime=*) runtime=${1#--runtime=} ;;
    --backup=*) backup=${1#--backup=} ;;
    -h|--help) usage; exit 0 ;;
    *) fail "unknown argument: $1" ;;
  esac
  shift
done

case "$mode" in
  proofs|experiments|production) ;;
  *) fail 'mode must be proofs, experiments, or production' ;;
esac

case "$runtime" in
  python|lean4|docker|cli) ;;
  *) fail 'runtime must be python, lean4, docker, or cli' ;;
esac

case "$backup" in
  local|github|zenodo) ;;
  *) fail 'backup must be local, github, or zenodo' ;;
esac

script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
repo_root=$(CDPATH= cd "$script_dir/.." && pwd -P)

if [ ! -f "$repo_root/AI" ] || [ ! -f "$repo_root/AI_CONTEXT.json" ]; then
  fail 'run the repository-owned script from a complete QIK-VRT checkout'
fi

cat <<ENV
# QIK-VRT working-memory .env template
QIKVRT_REPOSITORY=Goldkelch/qik-vrt
QIKVRT_WORKING_MEMORY_MODE=$mode
QIKVRT_WORKING_MEMORY_RUNTIME=$runtime
QIKVRT_WORKING_MEMORY_BACKUP=$backup
QIKVRT_BOOT_PROFILE=all
QIKVRT_EXTERNAL_EFFECTS=disabled
ENV
