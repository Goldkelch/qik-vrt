#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Serialize, transport, deserialize and verify the epistemic-spiral state."""
from __future__ import annotations
import argparse, base64, hashlib, json
from pathlib import Path
from typing import Any

EXPECTED={"ar","de","en","es","fr","hi","id","it","ja","ko","pt_BR","ru","tr","zh_CN"}

def canonical(value:Any)->bytes:
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")

def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default="docs/terminal/epistemic-spiral")
    ap.add_argument("--receipt")
    ns=ap.parse_args()
    root=Path(ns.root)
    state=json.loads((root/"state.json").read_text(encoding="utf-8"))
    locales=json.loads((root/"locales.json").read_text(encoding="utf-8"))
    if state.get("schema")!="qikvrt_epistemic_spiral_state_v1":
        raise SystemExit("BLOCK: state schema mismatch")
    if locales.get("schema")!="qikvrt_epistemic_spiral_locales_v1":
        raise SystemExit("BLOCK: locale schema mismatch")
    if set(locales.get("locales",{}))!=EXPECTED:
        raise SystemExit("BLOCK: target locale coverage mismatch")

    payload={"state":state,"locales":locales}
    serialized=canonical(payload)
    wire=base64.b64encode(serialized)
    restored=base64.b64decode(wire,validate=True)
    reparsed=json.loads(restored.decode("utf-8"))
    reserialized=canonical(reparsed)
    identity=(serialized==restored==reserialized)
    receipt={
      "schema":"qikvrt_epistemic_spiral_roundtrip_receipt_v1",
      "source_root":str(root),
      "payload_sha256":sha(serialized),
      "wire_sha256":sha(wire),
      "serialized_bytes":len(serialized),
      "wire_bytes":len(wire),
      "locale_count":len(EXPECTED),
      "serialize_deserialize_identity":identity,
      "carrier":"REPOSITORY_OR_BOUND_RUNTIME",
      "transport_ack":identity,
      "effect_ack_done":False,
      "physical_universe_claim_confirmed":False
    }
    encoded=json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+"\n"
    print(encoded,end="")
    if ns.receipt:
        Path(ns.receipt).write_text(encoded,encoding="utf-8")
    return 0 if identity else 2

if __name__=="__main__":
    raise SystemExit(main())
