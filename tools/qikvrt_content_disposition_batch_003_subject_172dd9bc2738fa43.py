#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Compatibility entrypoint for Subject-172 and later owner-return status."""
from __future__ import annotations
import pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
ROOT_STR=str(ROOT)
if ROOT_STR not in sys.path:sys.path.insert(0,ROOT_STR)
OWNER_RECEIPT=ROOT/'release/zenodo-corpus-proof-2026-07-28/canonical-union/content-disposition-batch-003/corrected-candidates/OWNER_RETURN_RECEIPT.json'
if __name__=='__main__' and OWNER_RECEIPT.is_file():
 from tools import qikvrt_remaining_corpus_corrected_candidates_owner_return as owner
 raise SystemExit(owner.compat_main())
from tools.qikvrt_content_disposition_batch_003_subject_172dd9bc2738fa43_legacy import *  # noqa: F401,F403
if __name__=='__main__':raise SystemExit(main())
