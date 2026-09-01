#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import argparse
import hashlib
import json
import pathlib
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MLP_SHA256 = "5a74c9645d6cdcb2d92770517e31eb7697e180b2ccc4b7fb777c9b558b84ae7e"
TCPIP_SOURCE_HEAD = "a71484ba02f6ebe9169af5a291244e99468caec3"
TCPIP_SOURCE_TREE = "b45556a6c4ea2d9946c73264c1ed47d4f3128a76"
NONCE = "QIKVRT-FIREFOX-LIVE-0001"


def page(head, tree):
    return f'''<!doctype html><html><head><meta charset="utf-8"><title>QIK-VRT MLP Firefox Live Observation</title>
<style>body{{font-family:system-ui;background:#0b1020;color:#eef;margin:0;padding:40px}}.card{{max-width:980px;margin:auto;background:#151c33;border:1px solid #5060a0;border-radius:18px;padding:28px;box-shadow:0 12px 50px #0008}}h1{{margin-top:0}}.ok{{color:#67e480}}.hold{{color:#ffd166}}.no{{color:#9aa6c8}}code{{word-break:break-all}}</style></head><body><div class="card">
<h1>QIK-VRT · MLP.TOS → Firefox live witness</h1>
<p class="ok">✓ MLP.TOS deterministic image bound: <code>{MLP_SHA256}</code></p>
<p class="ok">✓ Mega-ST guest TCP/IP predecessor bound: <code>{TCPIP_SOURCE_HEAD}</code></p>
<p class="ok">✓ Mega-ST guest TCP/IP predecessor tree: <code>{TCPIP_SOURCE_TREE}</code></p>
<p class="ok">✓ Firefox rendered this page and executed JavaScript.</p>
<p>Exact head: <code>{head}</code><br>Exact tree: <code>{tree}</code></p>
<p class="hold">● EFFECT_ACK_DONE = false — protected external effect not executed.</p>
<p class="no">● physical original Mega-ST execution = not claimed.</p>
<p id="ua">JavaScript witness pending…</p>
<script>document.getElementById('ua').textContent='Firefox JS witness: '+navigator.userAgent;fetch('/observed?nonce={NONCE}&ua='+encodeURIComponent(navigator.userAgent),{{cache:'no-store'}});</script>
</div></body></html>'''


def serve(args):
    output = pathlib.Path(args.observation)
    output.parent.mkdir(parents=True, exist_ok=True)
    html = page(args.head, args.tree).encode()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *vals):
            return

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(html)
                return
            if parsed.path == "/observed":
                q = urllib.parse.parse_qs(parsed.query)
                payload = {
                    "schema": "qikvrt_mlp_firefox_live_observation_v1",
                    "head_sha": args.head,
                    "tree_sha": args.tree,
                    "mlp_tos_sha256": MLP_SHA256,
                    "tcpip_source_head": TCPIP_SOURCE_HEAD,
                    "tcpip_source_tree": TCPIP_SOURCE_TREE,
                    "nonce": q.get("nonce", [""])[0],
                    "user_agent": q.get("ua", [""])[0],
                    "browser_javascript_observed": True,
                    "browser_rendering_observed": True,
                    "effect_ack_done": False,
                    "protected_external_effect": False,
                    "physical_megast_execution": False,
                }
                output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
                self.send_response(204)
                self.end_headers()
                return
            self.send_response(404)
            self.end_headers()

    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


def finalize(args):
    obs = json.loads(pathlib.Path(args.observation).read_text())
    if obs.get("nonce") != NONCE:
        raise SystemExit("HOLD: nonce mismatch")
    if not obs.get("browser_javascript_observed") or not obs.get("browser_rendering_observed"):
        raise SystemExit("HOLD: browser observation absent")
    if obs.get("effect_ack_done") or obs.get("protected_external_effect"):
        raise SystemExit("HOLD: observation may not invent an external effect")
    png = pathlib.Path(args.screenshot).read_bytes()
    if not png.startswith(b"\x89PNG\r\n\x1a\n") or len(png) < 1000:
        raise SystemExit("HOLD: screenshot is not a nontrivial PNG")
    obs["screenshot_sha256"] = hashlib.sha256(png).hexdigest()
    obs["firefox_version"] = args.firefox_version
    pathlib.Path(args.receipt).write_text(json.dumps(obs, sort_keys=True, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("serve")
    p.add_argument("--head", required=True)
    p.add_argument("--tree", required=True)
    p.add_argument("--observation", required=True)
    p.add_argument("--port", type=int, default=8772)
    p.set_defaults(func=serve)
    p = sub.add_parser("finalize")
    p.add_argument("--observation", required=True)
    p.add_argument("--screenshot", required=True)
    p.add_argument("--receipt", required=True)
    p.add_argument("--firefox-version", required=True)
    p.set_defaults(func=finalize)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
