#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
from __future__ import annotations

import argparse
import json
import stat
import zipfile
from pathlib import Path

EPOCH = (1980, 1, 1, 0, 0, 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="browser/firefox/qikvrt-terminal")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    source = Path(args.source)
    overlay = Path("distribution/qikvrt-mesh-appliance/firefox")
    files = {item.name: item.read_bytes() for item in source.iterdir() if item.is_file()}
    manifest = json.loads(files["manifest.json"])
    manifest["name"] = "QIKVRT Mesh Appliance Terminal"
    manifest["version"] = "1.1.0"
    manifest["description"] = "Firefox ESR adapter for the full QIK-VRT Responsibility Protocol appliance profile."
    scripts = list(manifest.get("background", {}).get("scripts", []))
    manifest["background"]["scripts"] = [
        "effect_ack_protocol.js",
        *[name for name in scripts if name != "effect_ack_protocol.js"],
    ]
    manifest["web_accessible_resources"] = [{
        "resources": ["selftest.html", "selftest.js", "effect_ack_protocol.js"],
        "matches": ["<all_urls>"],
    }]
    files["manifest.json"] = (
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode()
    for name in ("effect_ack_protocol.js", "selftest.html", "selftest.js"):
        files[name] = (overlay / name).read_bytes()

    background = files["background.js"].decode()
    verify_anchor = 'if (record.state !== "EFFECT_ACK_DONE" || record.ordinary_release !== true) return fail("full record is not release-eligible DONE");'
    verify_replacement = verify_anchor + '\n  const protocolCheck = await globalThis.QIKVRTProtocol.verify(record.responsibility_protocol || record);\n  if (!protocolCheck.ok) return fail(`Responsibility Protocol invalid: ${protocolCheck.reason}`);'
    if verify_anchor not in background:
        raise SystemExit("BLOCK: Firefox adapter protocol patch anchor unavailable")
    background = background.replace(verify_anchor, verify_replacement, 1)

    message_anchor = 'if (message.kind === "COMMIT_EFFECT") return commitEffect(message.payload).catch(error => fail(error.message));'
    message_replacement = message_anchor + '\n  if (message.kind === "OBSERVE_EFFECT_STATE") return backendRequest("/terminal/state", {method: "GET"}).catch(error => fail(error.message));'
    if message_anchor not in background:
        raise SystemExit("BLOCK: Firefox adapter observation patch anchor unavailable")
    files["background.js"] = background.replace(message_anchor, message_replacement, 1).encode()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(name, EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, files[name])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
