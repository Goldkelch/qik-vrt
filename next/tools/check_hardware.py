#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Generated implementation: OpenAI Codex.
"""Independent truth-table oracle, C90 via Rust/RTL comparison and synthesis smoke."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--binary", default=str(ROOT/"target/release/qikvrt-next"))
    p.add_argument("--ghdl", default="ghdl")
    p.add_argument("--output", type=Path)
    args=p.parse_args()
    vectors=subprocess.check_output([args.binary,"vectors"],timeout=20)
    rows=vectors.decode().splitlines()
    for row in rows:
        items=row.split()
        lut,a,b,requested,binding,authority,distinction,drift,state=map(int,items[:9])
        value=int(items[9],16); valid=int(items[10])
        expected_state=requested if (binding,authority,distinction,drift)==(1,1,1,0) and requested<3 else 1
        expected_value=0
        if expected_state==2:
            for bit in range(32):
                index=2*((a>>bit)&1)+((b>>bit)&1)
                expected_value|=((lut>>index)&1)<<bit
        assert (state,value,valid)==(expected_state,expected_value,int(expected_state==2)),row
    assert len(rows)==16*2*2*4*3**4
    with tempfile.TemporaryDirectory(prefix="qikvrt-hdl-") as work:
        work=Path(work);(work/"vectors.txt").write_bytes(vectors)
        files=[ROOT/"reference/hardware/vhdl/qikvrt_metatransistor_pkg.vhd",ROOT/"hardware/metatransistor_tile.vhd",ROOT/"hardware/tb_tile.vhd"]
        def ghdl(*options):return subprocess.check_output([args.ghdl,*map(str,options)],cwd=work,stderr=subprocess.STDOUT,timeout=60)
        ghdl("-a","--std=08",*files)
        ghdl("-e","--std=08","tb_tile")
        simulation=ghdl("-r","--std=08","tb_tile","--assert-level=error")
        observed=(work/"observed.txt").read_text().splitlines()
        expected=[" ".join(r.split()[8:]) for r in rows]
        assert observed==expected,"RTL readback differs from C90 through Rust vectors"
        netlist=ghdl("--synth","--std=08","metatransistor_tile")
        assert b"entity metatransistor_tile" in netlist
    result={"state":"PASS","scope":"finite_boolean_and_guard_carriers_with_backpressure",
        "vectors":len(rows),"c90_through_rust_vector_sha256":hashlib.sha256(vectors).hexdigest(),
        "rtl_readback_sha256":hashlib.sha256(("\n".join(observed)+"\n").encode()).hexdigest(),
        "synthesis_netlist_sha256":hashlib.sha256(netlist).hexdigest(),"synthesis_netlist_bytes":len(netlist),
        "simulation":simulation.decode().strip(),"fpga_placement_timing_or_physical_boot":False}
    if args.output: args.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":main()
