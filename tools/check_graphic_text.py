#!/usr/bin/env python3
import json, pathlib, sys

def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: check_graphic_text.py MANIFEST OVERLAY_TEXT")
    manifest = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    expected = manifest["authoritative_lines"]
    actual = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8").splitlines()
    if actual != expected:
        print("GRAPHIC_TEXT_MISMATCH")
        print("expected:", repr(expected))
        print("actual:  ", repr(actual))
        return 1
    print("GRAPHIC_TEXT_EXACT_MATCH")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
