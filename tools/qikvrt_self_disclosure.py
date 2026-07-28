#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
import argparse,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
DOC=ROOT/'.well-known'/'qik-vrt-self-disclosure.json'
def main():
 p=argparse.ArgumentParser(); p.add_argument('command',choices=['show','capabilities','status']); a=p.parse_args(); d=json.loads(DOC.read_text())
 if a.command=='show': out=d
 elif a.command=='capabilities': out={'schema':d['schema'],'capabilities':d['capabilities']}
 else: out={'schema':d['schema'],'service':d['service'],'state':d['state'],'completion_claims':d['completion_claims']}
 print(json.dumps(out,sort_keys=True,indent=2)); return 0
if __name__=='__main__': sys.exit(main())
