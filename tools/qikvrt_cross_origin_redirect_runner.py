#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Run one Python entry point with cross-origin authorization stripping."""
from __future__ import annotations

import runpy
import sys
from typing import Any
import urllib.parse
import urllib.request


def _origin(url: str) -> tuple[str, str, int | None]:
    parsed = urllib.parse.urlsplit(url)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    port = parsed.port
    if port is None:
        if scheme == "https":
            port = 443
        elif scheme == "http":
            port = 80
    return scheme, host, port


class CrossOriginAuthorizationRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Preserve normal redirects while never forwarding Authorization cross-origin."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None and _origin(req.full_url) != _origin(redirected.full_url):
            redirected.remove_header("Authorization")
        return redirected


def install_cross_origin_safe_opener() -> urllib.request.OpenerDirector:
    opener = urllib.request.build_opener(CrossOriginAuthorizationRedirectHandler())
    urllib.request.install_opener(opener)
    return opener


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("usage: qikvrt_cross_origin_redirect_runner.py SCRIPT [ARG ...]")
    script = sys.argv[1]
    sys.argv = sys.argv[1:]
    install_cross_origin_safe_opener()
    runpy.run_path(script, run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
