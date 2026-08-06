#!/usr/bin/env bash
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
set -euo pipefail
cd "$(dirname "$0")"
export SOURCE_DATE_EPOCH="1785945600"
xelatex -interaction=nonstopmode -halt-on-error QIK-VRT_QCE_Fachartikel_DE_2026-08-05.tex
xelatex -interaction=nonstopmode -halt-on-error QIK-VRT_QCE_Fachartikel_DE_2026-08-05.tex
rm -f QIK-VRT_QCE_Fachartikel_DE_2026-08-05.aux \
      QIK-VRT_QCE_Fachartikel_DE_2026-08-05.log \
      QIK-VRT_QCE_Fachartikel_DE_2026-08-05.out \
      QIK-VRT_QCE_Fachartikel_DE_2026-08-05.toc
