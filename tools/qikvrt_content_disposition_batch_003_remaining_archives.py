#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Compatibility entrypoint for archive disposition and owner-return status."""
from __future__ import annotations
import pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
ROOT_STR=str(ROOT)
if ROOT_STR not in sys.path:sys.path.insert(0,ROOT_STR)
OWNER_RECEIPT=ROOT/'release/zenodo-corpus-proof-2026-07-28/canonical-union/content-disposition-batch-003/corrected-candidates/OWNER_RETURN_RECEIPT.json'
from tools.qikvrt_content_disposition_batch_003_remaining_archives_legacy import *  # noqa: F401,F403
if OWNER_RECEIPT.is_file():
 from tools import qikvrt_remaining_corpus_corrected_candidates_owner_return as _owner
 NEXT_EFFECT=_owner.NEXT_EFFECT
 NEXT_SUBJECT_ID=_owner.NEXT_SUBJECT_ID
 TOOL_REL=_owner.TOOL_REL
 build_progress_projection=_owner.build_progress_projection
 validate_progress_projection=_owner.validate_progress_projection
 verify_materialized=_owner.verify_materialized
 materialize=_owner.materialize
 main=_owner.main
if __name__=='__main__':raise SystemExit(main())
