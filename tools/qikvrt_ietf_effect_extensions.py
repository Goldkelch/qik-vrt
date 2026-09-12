# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Offline source/precedence checks and a bounded readback decision model.

This is NOT an HTTP, authentication, durable-execution, or publication adapter.
VerifiedContext represents assertions supplied by a trusted verifier, never
booleans accepted from an untrusted wire record. Synthetic tests do not prove
that any such verifier or remote effect has executed.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shutil
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET
from dataclasses import dataclass, fields, replace
from pathlib import Path
from urllib.parse import urlsplit

PROFILE = "eap-http-readback-1"
ROOT = Path(__file__).resolve().parents[1]
POLICY = "policy/QIKVRT_IETF_EFFECT_EXTENSIONS_V1.json"
REQUEST = "state/delivery/requests/IETF_EFFECT_ACK_EXTENSIONS_V1.json"
MAX_BYTES = 65536
DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")
CHALLENGE = re.compile(r"[0-9a-f]{64}\Z")
MEMBERS = set("profile action_hash authorization_record_hash execution_id challenge observer source_uri resource_uri resource_version outcome evidence sequence previous_receipt_hash".split())
SPINE = [
    "P0_MANIFEST_LATEST_KNOWLEDGE", "P1_BUILD_ONE_INTEGRATION_HEAD",
    "P2_VALIDATE_EXACT_INTEGRATION_HEAD", "P3_REVIEW_EXACT_INTEGRATION_HEAD",
    "P4_REOBSERVE_POST_REVIEW_EXACT_HEAD", "P5_LEGITIMATE_PROMOTION_TO_TRUSTED_MAIN",
    "P6_REOBSERVE_EXACT_TRUSTED_MAIN_HEAD", "P7_DERIVE_BOUND_EXTERNAL_OBLIGATIONS",
]


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON member")
        result[key] = value
    return result


def invalid_number(value: str) -> None:
    raise ValueError("unsupported JSON number: " + value)


def parse_json(raw: bytes) -> object:
    require(len(raw) <= MAX_BYTES, "oversized auxiliary object")
    require(not raw.startswith(b"\xef\xbb\xbf"), "JSON BOM forbidden")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object,
                          parse_float=invalid_number, parse_constant=invalid_number)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("invalid bounded JSON") from exc


def bounded(value: object, maximum: int) -> bool:
    return isinstance(value, str) and 1 <= len(value) <= maximum and all(32 <= ord(c) <= 126 for c in value)


def digest(value: object) -> bool:
    return isinstance(value, str) and DIGEST.fullmatch(value) is not None


def https_uri(value: object) -> bool:
    if not bounded(value, 2048) or " " in value:
        return False
    try:
        parsed = urlsplit(value)
        _ = parsed.port
        return parsed.scheme == "https" and bool(parsed.hostname) and parsed.username is None and parsed.password is None and not parsed.fragment
    except ValueError:
        return False


def validate_readback(value: object) -> dict:
    require(isinstance(value, dict) and set(value) == MEMBERS, "closed readback members")
    r = value
    require(r["profile"] == PROFILE, "unsupported profile")
    for key in ("action_hash", "authorization_record_hash"):
        require(digest(r[key]), "invalid " + key)
    for key in ("execution_id", "observer"):
        require(bounded(r[key], 256), "invalid " + key)
    require(isinstance(r["challenge"], str) and CHALLENGE.fullmatch(r["challenge"]) is not None, "invalid challenge")
    require(https_uri(r["source_uri"]), "invalid source URI")
    require(r["resource_uri"] is None or https_uri(r["resource_uri"]), "invalid resource URI")
    require(r["resource_version"] is None or bounded(r["resource_version"], 256), "invalid resource version")
    require(r["outcome"] in ("CONFIRMED", "REFUTED", "UNKNOWN"), "invalid outcome")
    evidence = r["evidence"]
    require(isinstance(evidence, list) and len(evidence) <= 128 and all(digest(x) for x in evidence), "invalid evidence set")
    require(evidence == sorted(set(evidence)), "evidence must be sorted and unique")
    require(type(r["sequence"]) is int and 1 <= r["sequence"] <= 9007199254740991, "invalid sequence")
    require((r["sequence"] == 1 and r["previous_receipt_hash"] is None) or
            (r["sequence"] > 1 and digest(r["previous_receipt_hash"])), "invalid chain shape")
    if r["outcome"] != "UNKNOWN":
        require(r["resource_uri"] is not None and r["resource_version"] is not None and bool(evidence), "authoritative outcome requires resource and evidence")
    return r


@dataclass(frozen=True)
class VerifiedContext:
    action_hash: str
    authorization_record_hash: str
    execution_id: str
    challenge: str
    observer: str
    source_uri: str
    resource_uri: str
    resource_version: str
    authorization_valid: bool = False
    subject_current: bool = False
    execution_binding_valid: bool = False
    observer_authorized: bool = False
    source_authenticated: bool = False
    fresh_observation: bool = False
    requirements_valid: bool = False
    evidence_verified: bool = False
    chain_valid: bool = False
    postcondition_determined: bool = False
    postcondition_satisfied: bool = False


def classify_readback(raw: bytes, context: VerifiedContext) -> str:
    """Reference relation only; cannot authenticate or authorize an action."""
    if type(context) is not VerifiedContext:
        return "UNKNOWN"
    try:
        record = validate_readback(parse_json(raw))
        gates = ("authorization_valid", "subject_current", "execution_binding_valid",
                 "observer_authorized", "source_authenticated", "fresh_observation",
                 "requirements_valid", "evidence_verified", "chain_valid", "postcondition_determined")
        if any(getattr(context, key) is not True for key in gates):
            return "UNKNOWN"
        for key in ("action_hash", "authorization_record_hash", "execution_id", "challenge",
                    "observer", "source_uri", "resource_uri", "resource_version"):
            if record[key] != getattr(context, key):
                return "UNKNOWN"
        if type(context.postcondition_satisfied) is not bool:
            return "UNKNOWN"
        derived = "CONFIRMED" if context.postcondition_satisfied else "REFUTED"
        return derived if record["outcome"] == derived else "UNKNOWN"
    except (ValueError, TypeError, KeyError, RecursionError):
        return "UNKNOWN"


def fixture() -> tuple[dict, VerifiedContext]:
    record = dict(profile=PROFILE, action_hash="sha256:" + "1" * 64,
                  authorization_record_hash="sha256:" + "2" * 64,
                  execution_id="synthetic-execution", challenge="3" * 64,
                  observer="synthetic-observer", source_uri="https://source.example/status",
                  resource_uri="https://source.example/object/1", resource_version="v1",
                  outcome="CONFIRMED", evidence=["sha256:" + "4" * 64],
                  sequence=1, previous_receipt_hash=None)
    binding = {f.name: record[f.name] for f in fields(VerifiedContext) if f.name in record}
    booleans = {f.name: True for f in fields(VerifiedContext) if f.name not in binding}
    return record, VerifiedContext(**binding, **booleans)


def encode(value: object) -> bytes:
    # Fixtures contain ASCII and bounded integers only. Not a general JCS implementation.
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")


class ReadbackModelTests(unittest.TestCase):
    def test_confirmed_and_refuted_require_verified_predicates(self):
        r, c = fixture()
        self.assertEqual(classify_readback(encode(r), c), "CONFIRMED")
        r["outcome"] = "REFUTED"
        self.assertEqual(classify_readback(encode(r), replace(c, postcondition_satisfied=False)), "REFUTED")
        self.assertEqual(classify_readback(encode(r), c), "UNKNOWN")

    def test_each_missing_verification_fails_closed(self):
        r, c = fixture()
        for f in fields(c):
            if type(getattr(c, f.name)) is bool:
                with self.subTest(gate=f.name):
                    self.assertEqual(classify_readback(encode(r), replace(c, **{f.name: False})), "UNKNOWN")

    def test_each_subject_or_identity_mutation_fails_closed(self):
        r, c = fixture()
        for f in fields(c):
            if isinstance(getattr(c, f.name), str):
                with self.subTest(binding=f.name):
                    self.assertEqual(classify_readback(encode(r), replace(c, **{f.name: "different"})), "UNKNOWN")

    def test_unauthenticated_wire_booleans_are_not_context(self):
        r, _ = fixture()
        self.assertEqual(classify_readback(encode(r), {"authorization_valid": True}), "UNKNOWN")
        _, c = fixture()
        r["authenticated"] = True
        self.assertEqual(classify_readback(encode(r), c), "UNKNOWN")

    def test_duplicate_members_and_numbers(self):
        r, c = fixture()
        raw = encode(r)
        duplicate = raw[:-1] + b',"profile":"eap-http-readback-1"}'
        for bad in (duplicate, b'{"sequence":NaN}', b'{"sequence":1.5}', b"\xef\xbb\xbf" + raw, b"\xff", b" " * (MAX_BYTES + 1)):
            with self.subTest(raw=bad[:30]):
                self.assertEqual(classify_readback(bad, c), "UNKNOWN")

    def test_missing_evidence_and_bad_chain(self):
        r, c = fixture()
        changes = ({"evidence": []}, {"evidence": r["evidence"] * 2},
                   {"resource_version": None}, {"resource_uri": None},
                   {"sequence": True}, {"sequence": 2},
                   {"sequence": 9007199254740992},
                   {"previous_receipt_hash": "sha256:" + "5" * 64})
        for change in changes:
            with self.subTest(change=change):
                self.assertEqual(classify_readback(encode(dict(r, **change)), c), "UNKNOWN")

    def test_unknown_and_untrusted_directions_do_not_confirm(self):
        r, c = fixture()
        for change in ({"outcome": "UNKNOWN"}, {"outcome": "EFFECT_ACK_DONE"},
                       {"profile": "future-profile"}, {"source_uri": "http://source.example/status"}):
            with self.subTest(change=change):
                self.assertEqual(classify_readback(encode(dict(r, **change)), c), "UNKNOWN")

    def test_receipt_successor_still_needs_verified_chain(self):
        r, c = fixture()
        r.update(sequence=2, previous_receipt_hash="sha256:" + "5" * 64)
        self.assertEqual(classify_readback(encode(r), replace(c, chain_valid=False)), "UNKNOWN")
        self.assertEqual(classify_readback(encode(r), c), "CONFIRMED")


def run_model_tests() -> int:
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReadbackModelTests))
    require(result.wasSuccessful(), "readback reference-model regressions")
    return result.testsRun


def check_sources(root: Path) -> dict:
    sys.path.insert(0, str(root))
    from tools.qikvrt_execution_precedence import validate_policy, next_eligible
    extension = json.loads((root / POLICY).read_text())
    parent = json.loads((root / extension["extends"]).read_text())
    validate_policy(parent)
    require(parent["canonical_spine"] == SPINE, "canonical spine changed")
    for index, node in enumerate(SPINE):
        require(parent["phases"][node]["requires"] == ([] if index == 0 else [SPINE[index - 1]]), "phase predecessor changed")
    require(extension["preserved_boundaries"]["predecessor_evidence_transfer"] is False, "evidence transfer forbidden")
    additions = extension["external_fanout_extension"]
    require(set(additions) == {"E4_IETF"}, "unexpected additive edge")
    combined = copy.deepcopy(parent)
    for name, edge in additions.items():
        require(name not in combined["external_fanout"]["edges"] or combined["external_fanout"]["edges"][name] == edge, "conflicting edge")
        combined["external_fanout"]["edges"][name] = edge
    validate_policy(combined)
    ready = dict.fromkeys(SPINE, "SATISFIED")
    require("E4_IETF" in next_eligible(combined, ready)["eligible"], "IETF must follow satisfied common barrier")
    for blocked in ("UNKNOWN", "STALE", "FAILED", "UNBOUND", "UNSATISFIED"):
        require("E4_IETF" not in next_eligible(combined, dict(ready, **{SPINE[-1]: blocked}))["eligible"], "IETF bypassed barrier")
    request = json.loads((root / REQUEST).read_text())
    require(request["operation"]["future_binding"]["exact_main_sha"] is None, "source is not an execution receipt")
    require(all(value is False for value in request["completion_claims"].values()), "unearned completion claim")
    inventory = []
    for draft in request["operation"]["drafts"]:
        path = root / draft["source"]
        data = path.read_bytes()
        xml = ET.fromstring(data)
        require(xml.tag == "rfc" and xml.get("version") == "3", "not RFCXML v3")
        require(xml.get("docName") == draft["candidate_name"], "draft name mismatch")
        require(xml.get("ipr") == "trust200902" and xml.get("category") == "exp", "draft metadata changed")
        require(xml.findtext("front/author/address/email") == "ingolf.lohmann@live.com", "author binding mismatch")
        require(draft["submission_id"] is None and draft["public_readback"] is None, "source manifest is not publication evidence")
        inventory.append(dict(path=draft["source"], name=draft["candidate_name"], bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
    http_text = (root / request["operation"]["drafts"][0]["source"]).read_text()
    for marker in (PROFILE, "Authoritative Effect Readback", "UNKNOWN", "protocol_hash", "prepare-envelope", "readback =", "Replay, Crashes and Unknown Outcomes", "Backward Compatibility", "HTML Integration", "MUST NOT execute the protected effect"):
        require(marker in http_text, "missing normative section: " + marker)
    return {"schema": "qikvrt_ietf_extension_source_check_v1", "draft_sources": inventory,
            "scope": "SOURCE_AND_FINITE_REFERENCE_MODEL_ONLY", "P2_complete": False,
            "native_review": False, "external_submission": False,
            "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test-only", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        tests = run_model_tests()
        if args.self_test_only:
            print(json.dumps({"model_test_methods": tests, "scope": "SYNTHETIC_REFERENCE_ONLY"}))
            return 0
        result = check_sources(ROOT)
        result["model_test_methods"] = tests
        result["head"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        result["tree"] = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip()
        if args.out:
            out = args.out.resolve()
            require(not out.is_relative_to(ROOT.resolve()), "outputs must be outside immutable source checkout")
            out.mkdir(parents=True, exist_ok=True)
            for item in result["draft_sources"]:
                shutil.copyfile(ROOT / item["path"], out / (item["name"] + ".xml"))
            (out / "SOURCE_CHECK.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, KeyError, ET.ParseError, subprocess.CalledProcessError) as exc:
        print("HOLD_UNVERIFIED: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
