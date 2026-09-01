#!/usr/bin/env python3
import argparse, struct
from pathlib import Path

ap=argparse.ArgumentParser(); ap.add_argument('--text',required=True); ap.add_argument('--output',required=True)
a=ap.parse_args(); text=Path(a.text).read_bytes()
# Atari executable header: magic, text, data, bss, symbols, reserved, flags, absflag.
# absflag=1 because QIKNET.S is fully position-independent and contains no relocation table.
hdr=struct.pack('>HIIIIIIH',0x601A,len(text),0,0,0,0,0,1)
Path(a.output).write_bytes(hdr+text)
print(f'QIKNET.PRG bytes={len(hdr)+len(text)} text={len(text)}')
