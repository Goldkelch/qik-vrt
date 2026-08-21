#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def classify(snapshot):
    repair = bool(snapshot.get("repair"))
    if not repair:
        return {"state": "NOT_REPAIR", "closed": False}
    if not snapshot.get("promotion_bound", False):
        return {"state": "NEED_PROMOTION_BINDING", "closed": False}
    if not snapshot.get("effective_on_main", False):
        return {"state": "VERIFIED_NOT_EFFECTIVE", "closed": False}
    if not snapshot.get("regression_probe_success", False):
        return {"state": "EFFECTIVE_UNPROBED", "closed": False}
    return {"state": "CLOSED", "closed": True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    snapshot = json.loads(Path(args.input).read_text())
    result = classify(snapshot)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["state"] in {"NOT_REPAIR", "CLOSED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
