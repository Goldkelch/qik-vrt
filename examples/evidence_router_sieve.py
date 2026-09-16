# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Local fixture demonstration; NOT Firefox, guest execution or live GitHub.

python3 -B examples/evidence_router_sieve.py --head <40hex> --tree <40hex> \
    --directory /a/new/empty/directory
"""
from dataclasses import asdict
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qikvrt_evidence_router import (Observation, ReceiptJournal, Relation,
                                  Router, Subject, canonical)


def sieve(limit: int) -> list[int]:
    marks = [True] * (limit + 1)
    marks[:2] = [False, False]
    for p in range(2, limit + 1):
        if marks[p]:
            for multiple in range(p * p, limit + 1, p):
                marks[multiple] = False
    return [n for n, prime in enumerate(marks) if prime]


def validate_primes(_relation: Relation, payload: bytes) -> bool:
    """A different algorithm validates the example payload, not authority."""
    value = json.loads(payload)
    if set(value) != {"limit", "primes", "scope"} or value["scope"] != "LOCAL_FIXTURE":
        return False
    limit = value["limit"]
    if type(limit) is not int or not 2 <= limit <= 1000:
        return False
    expected = [n for n in range(2, limit + 1)
                if all(n % divisor for divisor in range(2, n))]
    return value["primes"] == expected


class LocalFixtureObserver:
    """Explicitly reads local fixture bytes; no remote freshness claim."""

    def __init__(self, directory: Path, payloads: dict[str, Path]):
        self.directory, self.payloads = directory, payloads

    def read_subject(self) -> Subject:
        return Subject(**json.loads((self.directory / "subject.json").read_bytes()))

    def read_relation(self, relation: Relation, challenge: str) -> Observation:
        payload = self.payloads[relation.identity].read_bytes()
        return Observation(relation.identity, self.read_subject(), relation.receipt,
                           challenge, payload)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default="Goldkelch/qik-vrt")
    parser.add_argument("--head", required=True)
    parser.add_argument("--tree", required=True)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    subject = Subject(args.repository, args.head, args.tree)
    directory = args.directory.resolve()
    directory.mkdir(parents=True, exist_ok=False)  # never overwrite a prior run
    (directory / "subject.json").write_bytes(canonical(asdict(subject)) + b"\n")
    payload = canonical({"limit": 30, "primes": sieve(30), "scope": "LOCAL_FIXTURE"})
    edges, payloads = [], {}
    for identity, source, target in (
        ("terminal-transputer", "universal-terminal", "universal-cloud-transputer"),
        ("transputer-router", "universal-cloud-transputer", "evidence-router"),
    ):
        path = directory / (identity + ".json")
        path.write_bytes(payload)
        address = "urn:qikvrt:fixture:" + identity
        payloads[address] = path
        edges.append(Relation(address, source, target, subject, path.as_uri(),
                              hashlib.sha256(payload).hexdigest(), (path.as_uri(),)))
    journal = ReceiptJournal(directory / "receipts.sqlite")
    router = Router(subject, edges, LocalFixtureObserver(directory, payloads),
                    validate_primes, journal, observer_id="local-file-fixture-reader",
                    validator_id="trial-division-example-validator")
    decision = router.route("universal-terminal", "evidence-router")
    report = {
        "scope": "LOCAL_FIXTURE_ONLY", "subject": asdict(subject),
        "route": list(decision.route.nodes), "cost": decision.route.cost,
        "primes": sieve(30), "journal": str(journal.path),
        "receipt_digest": decision.journal_digest,
        "readback_matches": journal.read(decision.journal_digest)["subject"] == asdict(subject),
        "full_three_phase_cycle": False, "live_repository_validation": False,
        "effect_ack_done": False,
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
