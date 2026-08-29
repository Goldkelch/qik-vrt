import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.issue_agent.binding import (
    INTAKE_CODE_PATHS,
    canonical_bytes,
    issue_snapshot,
    json_loads_strict,
    validate_request,
    worktree_code_sha256,
)
from scripts.issue_agent.epoch import build_epoch, prepare, reduce_receipts, run_lane
from scripts.issue_agent.infer import SYSTEM_PROMPT, deterministic_answer
from scripts.issue_agent.handlers import descriptor_sha256, extract_owner_contract, unavailable_descriptor
from scripts.issue_agent.materialize import event_binding, repository_context
from scripts.issue_agent.promote import promote
from scripts.issue_agent.validate import section as answer_section
from scripts.issue_agent.validate import validate


AUTHORITY = "Goldkelch/qik-vrt"
MIRROR = "ingolf-lohmann/qik-vrt"
SOURCE_TIME = "2026-08-28T18:04:00Z"


def write_sidecar(path: Path) -> None:
    path.with_suffix(".sha256").write_text(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n",
        encoding="utf-8",
    )


class ValidateIssueAgentBundleTest(unittest.TestCase):
    @staticmethod
    def owner_cycle_contract() -> dict:
        return {
            "schema": "qikvrt_owner_observed_repository_work_cycle_v1",
            "repository": AUTHORITY,
            "carrier_pr": 902,
            "observed_head": "4" * 40,
            "observed_tree": "9" * 40,
            "authority_main": "1" * 40,
            "cycle": [
                "EXTERNAL_REQUEST_OR_EVENT",
                "EXACT_BINDING",
                "CLASSIFY",
                "WORK",
                "RESULT",
                "MATERIALIZE",
                "REOBSERVE",
                "TERMINAL_STATUS",
                "REPORT",
                "RETURN_TO_ZERO",
            ],
            "observed_repository_reaction": {"d0": 2, "state": "REOBSERVE"},
            "finding": "One bounded repository work cycle is externally observable.",
            "required_future_behavior": ["Persist the finding.", "Reobserve one exact next turn."],
            "non_claims": {
                "independent_approval": False,
                "merge": False,
                "authority_main_effect": False,
                "authority_mirror_synchronization": False,
                "publication": False,
                "deployment": False,
                "PASS": False,
                "FINAL_PASS": False,
                "EFFECT_ACK_DONE": False,
                "authority_review_fanout_end_to_end_observed": False,
            },
        }

    @classmethod
    def owner_cycle_body(cls, contract: dict) -> str:
        return (
            "<!-- qikvrt-owner-insight:external-repository-work-cycle-v1 -->\n"
            "```json\n"
            + json.dumps(contract, sort_keys=True)
            + "\n```\n"
        )

    def make_request(
        self,
        directory: Path,
        *,
        body: str = "",
        actor: str = "ingolf-lohmann",
        selected_author: str | None = None,
        selected_source: str = "ISSUE_COMMENT",
        author_type: str = "User",
        mesh_nodes: list[str] | None = None,
    ) -> tuple[dict, dict, dict, str]:
        directory.mkdir(parents=True, exist_ok=True)
        selected_author = selected_author or actor
        mesh_nodes = mesh_nodes or [AUTHORITY, MIRROR]
        registered = sorted(node for node in mesh_nodes if node != AUTHORITY)
        context = "repository context\n"
        (directory / "CONTEXT.md").write_text(context, encoding="utf-8")
        policy_path = ROOT / "policy/ISSUE_AGENT_DETERMINISTIC_INTAKE_V1.json"
        registry_path = ROOT / "registry/NODEMESH_INDEX.json"
        policy_bytes = policy_path.read_bytes()
        policy = json.loads(policy_bytes)
        request_fields = {
            "repository": AUTHORITY,
            "issue_number": 76,
            "title": "Owner work order",
            "body": body if selected_source == "ISSUE_BODY" else "",
            "author": actor,
            "author_type": author_type,
            "html_url": "https://github.com/Goldkelch/qik-vrt/issues/76",
            "created_at": "2026-08-28T18:00:00Z",
            "updated_at": SOURCE_TIME,
        }
        body_sha256 = hashlib.sha256(body.encode()).hexdigest()
        comment = selected_source == "ISSUE_COMMENT"
        trigger = {
            "event_name": "issue_comment" if comment else "issues",
            "event_action": "created" if comment else "opened",
            "actor_login": actor,
            "selected_author_login": selected_author,
            "selected_author_association": "MEMBER",
            "selected_source": selected_source,
            "selected_body": body,
            "selected_body_sha256": body_sha256,
            "comment_id": 5456017224 if comment else None,
            "comment_node_id": "IC_test" if comment else None,
            "comment_url": "https://github.com/Goldkelch/qik-vrt/issues/76#issuecomment-5456017224" if comment else None,
            "source_updated_at": SOURCE_TIME,
        }
        binding = {
            "event_name": trigger["event_name"],
            "event_action": trigger["event_action"],
            "issue_number": 76,
            "source_updated_at": SOURCE_TIME,
            "comment_id_or_null": trigger["comment_id"],
            "comment_node_id_or_null": trigger["comment_node_id"],
            "comment_url_or_null": trigger["comment_url"],
            "actor_login": actor,
            "selected_author_association": "MEMBER",
            "selected_author_login": selected_author,
            "selected_source": selected_source,
            "selected_body_sha256": body_sha256,
            "issue_snapshot_sha256": hashlib.sha256(canonical_bytes(issue_snapshot(request_fields))).hexdigest(),
            "context_sha256": hashlib.sha256(context.encode()).hexdigest(),
            "authority_head": "2" * 40,
            "authority_tree": "3" * 40,
            "handler_policy_sha256": hashlib.sha256(policy_bytes).hexdigest(),
            "registry_sha256": hashlib.sha256(registry_path.read_bytes()).hexdigest(),
            "intake_code_sha256": worktree_code_sha256(ROOT),
            "active_registered_nodes": registered,
            "active_mesh_nodes": sorted(mesh_nodes),
        }
        fingerprint = hashlib.sha256(canonical_bytes(binding)).hexdigest()
        request_value = {
            "schema": "qikvrt_issue_agent_request_v2",
            **request_fields,
            "trigger": trigger,
            "binding": binding,
            "request_fingerprint": fingerprint,
            "handler_policy": {
                "path": "policy/ISSUE_AGENT_DETERMINISTIC_INTAKE_V1.json",
                "sha256": binding["handler_policy_sha256"],
            },
            "registry": {
                "path": "registry/NODEMESH_INDEX.json",
                "sha256": binding["registry_sha256"],
                "active_registered_nodes": registered,
                "active_mesh_nodes": sorted(mesh_nodes),
            },
        }
        request_path = directory / "REQUEST.json"
        request_path.write_text(json.dumps(request_value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_sidecar(request_path)
        event_value = {
            "schema": "qikvrt_issue_agent_event_binding_v1",
            "binding": binding,
            "request_fingerprint": fingerprint,
        }
        event_path = directory / "EVENT.json"
        event_path.write_bytes(canonical_bytes(event_value))
        write_sidecar(event_path)
        issue = {
            "number": 76,
            "title": request_fields["title"],
            "body": request_fields["body"],
            "user": {"login": actor, "type": author_type},
        }
        return issue, request_value, policy, hashlib.sha256(policy_bytes).hexdigest()

    def refresh_evaluation(self, directory: Path) -> None:
        status = json.loads((directory / "STATUS.json").read_text(encoding="utf-8"))
        answer_bytes = (directory / "ANSWER.md").read_bytes()
        evaluation = {
            "schema": "qikvrt_issue_agent_evaluation_binding_v1",
            "answer_sha256": hashlib.sha256(answer_bytes).hexdigest(),
            "evaluation_completed": status["evaluation_completed"],
            "evaluation_mode": status["evaluation_mode"],
            "handler_id": status["handler_id"],
            "handler_sha256": status["handler_sha256"],
            "request_fingerprint": status["request_fingerprint"],
        }
        path = directory / "EVALUATION.json"
        path.write_bytes(canonical_bytes(evaluation))
        write_sidecar(path)

    def write_bound_answer(
        self,
        directory: Path,
        *,
        disposition: str,
        reason: str,
        next_action: str,
        gate: str,
        mode: str | None = None,
        handler_id: str | None = None,
        handler_sha256: str | None = None,
    ) -> None:
        status = json.loads((directory / "STATUS.json").read_text(encoding="utf-8"))
        mode = mode or status["evaluation_mode"]
        handler_id = handler_id or status["handler_id"]
        handler_sha256 = handler_sha256 or status["handler_sha256"]
        fingerprint = status["request_fingerprint"]
        (directory / "ANSWER.md").write_text(
            f"## Issue disposition\n\n{disposition}\n\n"
            f"## Disposition reason\n\n{reason}\n\n"
            f"## Required next action\n\n{next_action}\n\n"
            f"## Gate result\n\n{gate}\n\n"
            f"## Evaluation mode\n\n{mode}\n\n"
            f"## Handler id\n\n{handler_id}\n\n"
            f"## Handler SHA-256\n\n{handler_sha256}\n\n"
            f"## Request fingerprint\n\n{fingerprint}\n",
            encoding="utf-8",
        )

    def make_bundle(self, directory: Path) -> None:
        _, request, _, _ = self.make_request(directory)
        handler = {
            "handler_id": "OPTIONAL-GITHUB-MODELS-INFERENCE-V1",
            "model": "openai/gpt-4.1",
            "system_prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
        }
        handler_id = handler["handler_id"]
        handler_sha256 = hashlib.sha256(canonical_bytes(handler)).hexdigest()
        fingerprint = request["request_fingerprint"]
        (directory / "ANSWER.md").write_text(
            "## Issue disposition\n\nEXECUTE_NOW\n\n"
            "## Disposition reason\n\nThe request is clear and actionable.\n\n"
            "## Required next action\n\nExecute the smallest bounded work unit.\n\n"
            "## Gate result\n\nCONTINUE\n\n"
            "## Evaluation mode\n\nMODEL_INFERENCE\n\n"
            f"## Handler id\n\n{handler_id}\n\n"
            f"## Handler SHA-256\n\n{handler_sha256}\n\n"
            f"## Request fingerprint\n\n{fingerprint}\n",
            encoding="utf-8",
        )
        (directory / "STATUS.json").write_text(json.dumps({
            "schema": "qikvrt_issue_agent_status_v2",
            "status": "CONTINUE",
            "issue_materialized": True,
            "model_inference_completed": True,
            "deterministic_contract_completed": False,
            "evaluation_completed": True,
            "evaluation_mode": "MODEL_INFERENCE",
            "handler_id": handler_id,
            "handler_sha256": handler_sha256,
            "request_fingerprint": fingerprint,
            "issue_disposition": "EXECUTE_NOW",
            "disposition_reason": "The request is clear and actionable.",
            "next_action": "Execute the smallest bounded work unit.",
            "closure_recommended": False,
            "automatic_issue_close": False,
            "automatic_merge": False,
            "mirror_sync_required": False,
            "common_tag_required": False,
            "generated_at": SOURCE_TIME,
            "no_false_pass": True,
            "claims": {
                "PASS": False,
                "FINAL_PASS": False,
                "EFFECT_ACK_DONE": False,
                "MERGE": False,
                "ISSUE_CLOSE": False,
                "MIRROR_SYNC": False,
                "TAG": False,
                "PUBLICATION": False,
                "DEPLOYMENT": False,
            },
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.refresh_evaluation(directory)
        self.rebuild_reduction(directory)

    def rebuild_reduction(self, directory: Path) -> None:
        prepare(directory, verify_authority=False)
        with tempfile.TemporaryDirectory() as receipts_temp:
            receipts_root = Path(receipts_temp)
            lane_count = json.loads((directory / "WORK_EPOCH.json").read_text())["lane_count"]
            for index in range(lane_count):
                run_lane(directory, index, "42", "1", receipts_root / f"lane-{index}", verify_authority=False)
            reduce_receipts(directory, receipts_root, "42", "1", directory, verify_authority=False)

    def test_valid_bundle_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            validate(directory, verify_authority=False)

    def test_automatic_merge_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            status_path = directory / "STATUS.json"
            status = json.loads(status_path.read_text())
            status["automatic_merge"] = True
            status_path.write_text(json.dumps(status))
            with self.assertRaises(SystemExit):
                validate(directory, verify_authority=False)

    def test_missing_issue_disposition_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            status_path = directory / "STATUS.json"
            status = json.loads(status_path.read_text())
            del status["issue_disposition"]
            status_path.write_text(json.dumps(status))
            with self.assertRaises(SystemExit):
                validate(directory, verify_authority=False)

    def test_closure_disposition_may_use_none_next_action(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            self.write_bound_answer(
                directory,
                disposition="CLOSE_INVALID_OR_UNSUPPORTED",
                reason="The request is not reproducible from repository evidence.",
                next_action="NONE",
                gate="CONTINUE",
            )
            status_path = directory / "STATUS.json"
            status = json.loads(status_path.read_text())
            status.update({
                "issue_disposition": "CLOSE_INVALID_OR_UNSUPPORTED",
                "disposition_reason": "The request is not reproducible from repository evidence.",
                "next_action": "NONE",
                "closure_recommended": True,
            })
            status_path.write_text(json.dumps(status))
            self.refresh_evaluation(directory)
            self.rebuild_reduction(directory)
            validate(directory, verify_authority=False)

    def test_execute_now_remains_nonterminal_after_classification(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            promote(directory)
            status = json.loads((directory / "STATUS.json").read_text())
            self.assertEqual(status["status"], "CONTINUE")
            self.assertFalse(status["automatic_merge"])
            validate(directory, verify_authority=False)

    def test_blocked_disposition_stays_blocked_without_model(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            handler = unavailable_descriptor()
            handler_id = handler["handler_id"]
            handler_sha256 = descriptor_sha256(handler)
            self.write_bound_answer(
                directory,
                disposition="BLOCKED_WITH_NEXT_ACTION",
                reason="MODEL_INFERENCE_UNAVAILABLE",
                next_action="Resume the bounded issue transaction when a trusted inference or deterministic work-unit path is available.",
                gate="BLOCK",
                mode="UNAVAILABLE",
                handler_id=handler_id,
                handler_sha256=handler_sha256,
            )
            status_path = directory / "STATUS.json"
            status = json.loads(status_path.read_text())
            status.update({
                "model_inference_completed": False,
                "deterministic_contract_completed": False,
                "evaluation_completed": False,
                "evaluation_mode": "UNAVAILABLE",
                "handler_id": handler_id,
                "handler_sha256": handler_sha256,
                "issue_disposition": "BLOCKED_WITH_NEXT_ACTION",
                "disposition_reason": "MODEL_INFERENCE_UNAVAILABLE",
                "next_action": "Resume the bounded issue transaction when a trusted inference or deterministic work-unit path is available.",
                "closure_recommended": False,
            })
            status_path.write_text(json.dumps(status))
            self.refresh_evaluation(directory)
            self.rebuild_reduction(directory)
            promote(directory)
            self.assertEqual(json.loads(status_path.read_text())["status"], "BLOCK")
            validate(directory, verify_authority=False)

    def test_closure_becomes_candidate_not_merge_authority(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            self.write_bound_answer(
                directory,
                disposition="CLOSE_COMPLETED",
                reason="The canonical successor fully evidences repository completion.",
                next_action="NONE",
                gate="CONTINUE",
            )
            status_path = directory / "STATUS.json"
            status = json.loads(status_path.read_text())
            status.update({
                "issue_disposition": "CLOSE_COMPLETED",
                "disposition_reason": "The canonical successor fully evidences repository completion.",
                "next_action": "NONE",
                "closure_recommended": True,
            })
            status_path.write_text(json.dumps(status))
            self.refresh_evaluation(directory)
            self.rebuild_reduction(directory)
            promote(directory)
            promoted = json.loads(status_path.read_text())
            self.assertEqual(promoted["status"], "TERMINAL_CANDIDATE")
            self.assertFalse(promoted["automatic_merge"])
            self.assertFalse(promoted["automatic_issue_close"])
            self.assertEqual(promoted["authority_next_action"], "REQUEST_EXACT_HEAD_REVIEW")
            validate(directory, verify_authority=False)

    def test_real_owner_comments_use_deterministic_handlers_without_model(self):
        for marker, handler in (
            ("qikvrt-owner-fractal-physics-spacetime-additive-work-order-v1", "OWNER-FRACTAL-PHYSICS-SPACETIME-ADDITIVE-WORK-ORDER-V1"),
            ("qikvrt-root-blocker-repair-order-v1", "OWNER-REPOSITORY-NATIVE-ROOT-BLOCKER-REPAIR-V1"),
        ):
            with tempfile.TemporaryDirectory() as temp:
                body = f"<!-- {marker} -->\nExecute."
                issue, request, policy, policy_sha256 = self.make_request(Path(temp), body=body)
                answer = deterministic_answer(issue, request, policy, policy_sha256)
                self.assertIn("DETERMINISTIC_OWNER_CONTRACT", answer)
                self.assertIn(handler, answer)

    def test_pr904_owner_cycle_contract_is_deterministic_and_requires_reobservation(self):
        with tempfile.TemporaryDirectory() as temp:
            body = self.owner_cycle_body(self.owner_cycle_contract())
            issue, request, policy, policy_sha256 = self.make_request(Path(temp), body=body)
            handler = next(value for value in policy["handlers"] if value["handler_id"] == "OWNER-OBSERVED-REPOSITORY-WORK-CYCLE-V1")
            self.assertIsNotNone(extract_owner_contract(body, handler))
            answer = deterministic_answer(issue, request, policy, policy_sha256)
            self.assertIn("DETERMINISTIC_OWNER_CONTRACT_VALIDATED", answer)
            self.assertIn("REFERENCED_EVIDENCE_REQUIRES_EXACT_REOBSERVATION", answer)
            self.assertIn("OWNER-OBSERVED-REPOSITORY-WORK-CYCLE-V1", answer)
            self.assertIn("## Gate result\n\nCONTINUE", answer)

    def test_pr904_owner_cycle_contract_false_nonclaim_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            contract = self.owner_cycle_contract()
            contract["non_claims"]["PASS"] = True
            body = self.owner_cycle_body(contract)
            issue, request, policy, policy_sha256 = self.make_request(Path(temp), body=body)
            handler = next(value for value in policy["handlers"] if value["handler_id"] == "OWNER-OBSERVED-REPOSITORY-WORK-CYCLE-V1")
            self.assertIsNone(extract_owner_contract(body, handler))
            answer = deterministic_answer(issue, request, policy, policy_sha256)
            self.assertIn("DETERMINISTIC_REJECT", answer)
            self.assertIn("UNKNOWN_OR_AMBIGUOUS_OWNER_WORK_ORDER_MARKER", answer)

    def test_pr904_owner_cycle_promotes_only_to_continue(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            body = self.owner_cycle_body(self.owner_cycle_contract())
            issue, request, policy, policy_sha256 = self.make_request(directory, body=body)
            answer = deterministic_answer(issue, request, policy, policy_sha256)
            (directory / "ANSWER.md").write_text(answer, encoding="utf-8")
            fingerprint = request["request_fingerprint"]
            status = {
                "schema": "qikvrt_issue_agent_status_v2",
                "status": "CONTINUE",
                "issue_materialized": True,
                "model_inference_completed": False,
                "deterministic_contract_completed": True,
                "evaluation_completed": True,
                "evaluation_mode": "DETERMINISTIC_OWNER_CONTRACT",
                "handler_id": answer_section(answer, "Handler id"),
                "handler_sha256": answer_section(answer, "Handler SHA-256"),
                "request_fingerprint": fingerprint,
                "issue_disposition": "EXECUTE_NOW",
                "disposition_reason": answer_section(answer, "Disposition reason"),
                "next_action": answer_section(answer, "Required next action"),
                "closure_recommended": False,
                "automatic_issue_close": False,
                "automatic_merge": False,
                "mirror_sync_required": False,
                "common_tag_required": False,
                "generated_at": SOURCE_TIME,
                "no_false_pass": True,
                "claims": {
                    "PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False,
                    "MERGE": False, "ISSUE_CLOSE": False, "MIRROR_SYNC": False,
                    "TAG": False, "PUBLICATION": False, "DEPLOYMENT": False,
                },
            }
            (directory / "STATUS.json").write_text(json.dumps(status, indent=2, sort_keys=True) + "\n")
            self.refresh_evaluation(directory)
            self.rebuild_reduction(directory)
            promote(directory)
            validate(directory, verify_authority=False)
            self.assertEqual(json.loads((directory / "STATUS.json").read_text())["status"], "CONTINUE")

    def test_external_agent_credit_failure_is_redirect_only(self):
        with tempfile.TemporaryDirectory() as temp:
            body = "You don't have sufficient GitHub AI Credits to start a session"
            issue, request, policy, policy_sha256 = self.make_request(
                Path(temp),
                body=body,
                actor="copilot-agent[bot]",
                selected_source="ISSUE_BODY",
                author_type="Bot",
                mesh_nodes=[AUTHORITY],
            )
            answer = deterministic_answer(issue, request, policy, policy_sha256)
            self.assertIn("EXTERNAL_AGENT_FAILURE", answer)
            self.assertIn("EXTERNAL_AGENT_ADMISSION_FAILURE", answer)

    def test_untrusted_owner_marker_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            body = "<!-- qikvrt-root-blocker-repair-order-v1 -->"
            issue, request, policy, policy_sha256 = self.make_request(
                Path(temp), body=body, actor="mallory"
            )
            answer = deterministic_answer(issue, request, policy, policy_sha256)
            self.assertIn("DETERMINISTIC_REJECT", answer)
            self.assertIn("OWNER_MARKER_ACTOR_NOT_AUTHORIZED", answer)

    def test_trusted_sender_cannot_adopt_untrusted_marker_author(self):
        with tempfile.TemporaryDirectory() as temp:
            body = "<!-- qikvrt-root-blocker-repair-order-v1 -->"
            issue, request, policy, policy_sha256 = self.make_request(
                Path(temp),
                body=body,
                actor="ingolf-lohmann",
                selected_author="mallory",
            )
            answer = deterministic_answer(issue, request, policy, policy_sha256)
            self.assertIn("DETERMINISTIC_REJECT", answer)
            self.assertIn("OWNER_MARKER_ACTOR_NOT_AUTHORIZED", answer)

    def test_duplicate_request_keys_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON key: repository"):
            json_loads_strict(
                '{"schema":"qikvrt_issue_agent_request_v2",'
                '"repository":"Goldkelch/qik-vrt",'
                '"repository":"mallory/forged"}'
            )

    def test_non_finite_json_numbers_are_rejected(self):
        for token in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(token=token), self.assertRaisesRegex(
                ValueError, "non-finite JSON number"
            ):
                json_loads_strict('{"value":' + token + "}")

    def test_non_finite_owner_contract_is_not_admitted(self):
        contract = self.owner_cycle_contract()
        contract["observed_repository_reaction"]["d0"] = float("nan")
        body = self.owner_cycle_body(contract)
        policy = json.loads(
            (ROOT / "policy/ISSUE_AGENT_DETERMINISTIC_INTAKE_V1.json").read_text()
        )
        handler = next(
            item
            for item in policy["handlers"]
            if item["handler_id"] == "OWNER-OBSERVED-REPOSITORY-WORK-CYCLE-V1"
        )
        self.assertIsNone(extract_owner_contract(body, handler))

    def test_repository_context_reads_only_allowlisted_regular_files_from_exact_head(self):
        head = "a" * 40
        tree = (
            b"100644 blob 1111111111111111111111111111111111111111\tREADME.md\0"
            b"100644 blob 2222222222222222222222222222222222222222\tdocs/guide.md\0"
            b"100644 blob 3333333333333333333333333333333333333333\tprivate/prompt.md\0"
            b"120000 blob 4444444444444444444444444444444444444444\tdocs/link.md\0"
        )
        blobs = {
            f"{head}:README.md": b"trusted readme\n",
            f"{head}:docs/guide.md": b"trusted guide\n",
        }

        def git_output(command, stderr):
            self.assertEqual(stderr, subprocess.STDOUT)
            if command == ["git", "ls-tree", "-r", "-z", head]:
                return tree
            self.assertEqual(command[:2], ["git", "show"])
            return blobs[command[2]]

        with mock.patch(
            "scripts.issue_agent.materialize.subprocess.check_output",
            side_effect=git_output,
        ) as check_output:
            context = repository_context(head)

        self.assertIn("## `README.md`", context)
        self.assertIn("## `docs/guide.md`", context)
        self.assertNotIn("private/prompt.md", context)
        self.assertNotIn("docs/link.md", context)
        self.assertLess(context.index("README.md"), context.index("docs/guide.md"))
        self.assertEqual(check_output.call_count, 3)

    def test_self_consistent_comment_url_forgery_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            _, request, _, _ = self.make_request(Path(temp))
            forged_url = (
                "https://github.com/mallory/forged/issues/76"
                "#issuecomment-5456017224"
            )
            request["trigger"]["comment_url"] = forged_url
            request["binding"]["comment_url_or_null"] = forged_url
            request["request_fingerprint"] = hashlib.sha256(
                canonical_bytes(request["binding"])
            ).hexdigest()

            with self.assertRaisesRegex(
                ValueError,
                "issue-comment URL differs from bound repository, issue, or comment id",
            ):
                validate_request(request, repository_root=ROOT, verify_git=False)

    def test_request_rejects_authority_tree_not_bound_to_exact_head(self):
        with tempfile.TemporaryDirectory() as temp:
            _, request, _, _ = self.make_request(Path(temp))
            head = request["binding"]["authority_head"]
            exact_tree = request["binding"]["authority_tree"]
            exact_blobs = {
                "policy/ISSUE_AGENT_DETERMINISTIC_INTAKE_V1.json": (
                    ROOT / "policy/ISSUE_AGENT_DETERMINISTIC_INTAKE_V1.json"
                ).read_bytes(),
                "registry/NODEMESH_INDEX.json": (
                    ROOT / "registry/NODEMESH_INDEX.json"
                ).read_bytes(),
                **{path: (ROOT / path).read_bytes() for path in INTAKE_CODE_PATHS},
            }

            def git_read(repository_root, *args):
                self.assertEqual(repository_root, ROOT)
                if args == ("cat-file", "-e", f"{head}^{{commit}}"):
                    return b""
                if args == ("rev-parse", f"{head}^{{tree}}"):
                    return f"{exact_tree}\n".encode()
                if args[:1] == ("show",):
                    commit, path = args[1].split(":", 1)
                    self.assertEqual(commit, head)
                    return exact_blobs[path]
                self.fail(f"unexpected git binding read: {args}")

            with mock.patch("scripts.issue_agent.binding._git", side_effect=git_read):
                validate_request(request, repository_root=ROOT, verify_git=True)
                request["binding"]["authority_tree"] = "4" * 40
                request["request_fingerprint"] = hashlib.sha256(
                    canonical_bytes(request["binding"])
                ).hexdigest()
                with self.assertRaisesRegex(
                    ValueError, "authority tree differs from bound head tree"
                ):
                    validate_request(request, repository_root=ROOT, verify_git=True)

    def test_self_consistent_forged_handler_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            forged = {"handler_id": "FORGED-HANDLER-V1"}
            status_path = directory / "STATUS.json"
            status = json.loads(status_path.read_text())
            status["handler_id"] = forged["handler_id"]
            status["handler_sha256"] = descriptor_sha256(forged)
            status_path.write_text(json.dumps(status))
            self.write_bound_answer(
                directory,
                disposition=status["issue_disposition"],
                reason=status["disposition_reason"],
                next_action=status["next_action"],
                gate="CONTINUE",
                handler_id=forged["handler_id"],
                handler_sha256=descriptor_sha256(forged),
            )
            self.refresh_evaluation(directory)
            self.rebuild_reduction(directory)

            with self.assertRaisesRegex(
                SystemExit, "HANDLER_ID_DIFFERS_FROM_CANONICAL_ROUTE"
            ):
                validate(directory, verify_authority=False)

    def test_prepare_declares_but_does_not_invent_receipts(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_request(directory)
            prepare(directory, verify_authority=False)
            self.assertFalse((directory / "LANE_RECEIPTS.json").exists())
            self.assertFalse((directory / "FANIN.json").exists())
            epoch = json.loads((directory / "WORK_EPOCH.json").read_text())
            self.assertFalse(epoch["fanout_observed"])

    def test_quadratic_mapping_for_supported_node_counts(self):
        for count in (1, 2, 3, 16):
            with tempfile.TemporaryDirectory() as temp:
                nodes = [AUTHORITY] + [f"node-{i}/qik-vrt" for i in range(1, count)]
                _, request, _, _ = self.make_request(Path(temp), mesh_nodes=nodes)
                epoch, matrix = build_epoch(request, "a" * 64)
                self.assertEqual(epoch["lane_count"], count * count)
                self.assertEqual([lane["lane_index"] for lane in epoch["lanes"]], list(range(count * count)))
                self.assertEqual(len({lane["lane_id"] for lane in epoch["lanes"]}), count * count)
                self.assertEqual(len(matrix["include"]), count * count)

    def test_quadratic_lanes_bind_distinct_source_target_plans(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle = root / "bundle"
            self.make_request(bundle, mesh_nodes=[AUTHORITY, MIRROR])
            prepare(bundle, verify_authority=False)
            first = root / "lane-0"
            second = root / "lane-1"
            run_lane(bundle, 0, "42", "1", first, verify_authority=False)
            run_lane(bundle, 1, "42", "1", second, verify_authority=False)
            receipt_0 = json.loads((first / "LANE_RECEIPT.json").read_text())
            receipt_1 = json.loads((second / "LANE_RECEIPT.json").read_text())
            self.assertEqual(receipt_0["pair_plan"]["relation"], "SELF")
            self.assertEqual(receipt_1["pair_plan"]["relation"], "CROSS_REPOSITORY_PLANNED_ONLY")
            self.assertNotEqual(receipt_0["pair_plan"], receipt_1["pair_plan"])
            self.assertNotEqual(
                receipt_0["checks"]["pair_plan_sha256"],
                receipt_1["checks"]["pair_plan_sha256"],
            )
            self.assertFalse(
                receipt_1["pair_plan"]["operations"][2]["remote_target_contacted"]
            )

    def test_seventeen_nodes_exceed_one_bounded_epoch(self):
        with tempfile.TemporaryDirectory() as temp:
            nodes = [AUTHORITY] + [f"node-{i}/qik-vrt" for i in range(1, 17)]
            _, request, _, _ = self.make_request(Path(temp), mesh_nodes=nodes)
            with self.assertRaises(ValueError):
                build_epoch(request, "a" * 64)

    def test_reducer_rejects_missing_lane_and_writes_hold(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle = root / "bundle"
            receipts = root / "receipts"
            self.make_request(bundle)
            prepare(bundle, verify_authority=False)
            lane_count = json.loads((bundle / "WORK_EPOCH.json").read_text())["lane_count"]
            for index in range(lane_count - 1):
                run_lane(bundle, index, "42", "1", receipts / f"lane-{index}", verify_authority=False)
            with self.assertRaises(ValueError):
                reduce_receipts(bundle, receipts, "42", "1", bundle, verify_authority=False)
            self.assertEqual(json.loads((bundle / "FANIN.json").read_text())["state"], "HOLD")

    def test_reduction_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.make_bundle(directory)
            receipts_path = directory / "LANE_RECEIPTS.json"
            receipts = json.loads(receipts_path.read_text())
            receipts[0]["state"] = "DONE"
            receipts_path.write_text(json.dumps(receipts))
            write_sidecar(receipts_path)
            with self.assertRaises(SystemExit):
                validate(directory, verify_authority=False)

    def test_pull_request_comment_is_not_an_issue_work_order(self):
        issue = {"number": 76, "body": "", "user": {"login": "ingolf-lohmann"}}
        event = {
            "issue": {"number": 76, "pull_request": {"url": "https://example.invalid/pr"}},
            "comment": {"id": 1, "body": "x", "user": {"login": "ingolf-lohmann"}},
            "sender": {"login": "ingolf-lohmann"},
        }
        with self.assertRaises(SystemExit):
            event_binding(issue, event, "issue_comment", "created")

    def test_issue_agent_workflows_are_event_driven_and_single_writer(self):
        processing = (ROOT / ".github/workflows/issue-autonomous-processing.yml").read_text()
        terminal = (ROOT / ".github/workflows/issue-agent-autofinish.yml").read_text()
        self.assertFalse((ROOT / ".github/workflows/issue-agent-backlog-resume.yml").exists())
        self.assertIn("issue_comment:", processing)
        self.assertIn("strategy:", processing)
        self.assertIn("matrix:", processing)
        self.assertIn("workflow_run:", terminal)
        self.assertIn("workflows: [QIKVRT CI]", terminal)
        for workflow in (processing, terminal):
            self.assertNotIn("schedule:", workflow)
            self.assertNotIn("--force ", workflow)
            self.assertNotIn("checkout -B", workflow)
        self.assertEqual(processing.count('--force-with-lease="refs/heads/$branch:"'), 1)
        self.assertEqual(processing.count("contents: write"), 1)
        self.assertNotIn("gh pr merge", terminal)
        self.assertNotIn("contents: write", terminal)
        self.assertIn("evidence/issues/$ISSUE_NUMBER/epochs/$FINGERPRINT", processing)
        self.assertIn("candidate_class=WORK_ADMISSION", processing)
        self.assertIn("candidate_class=CLOSURE_CANDIDATE", processing)
        self.assertIn("existing immutable candidate has no supported class", processing)
        self.assertIn("colliding immutable candidate has no supported class", processing)
        self.assertIn("candidate_eligible=true\n            reuse_existing=true", processing)
        self.assertIn("steps.ref.outputs.candidate_class || steps.reuse.outputs.candidate_class", processing)
        self.assertIn('draft_args=(--draft)', processing)
        self.assertIn("READY_FOR_EXACT_HEAD_EXECUTOR_DISPATCH", terminal)
        self.assertIn("work_order_payload_sha256", terminal)
        self.assertIn("HOLD_EXECUTOR_NOT_REGISTERED", terminal)
        self.assertIn("READY_FOR_SEPARATE_EXPECTED_HEAD_AUTHORITY_DECISION", terminal)
        self.assertIn('test "$(jq -r .draft /tmp/pr-emission.json)" = true', terminal)
        self.assertIn("platform_transport_effects_declared", terminal)
        self.assertNotIn('external_effect:"NONE"', terminal)
        self.assertIn("HOLD_AUTHORITY_MAIN_DRIFT_AFTER_IMMUTABLE_REF_CREATE", processing)
        self.assertIn("Immutable candidate ref $BRANCH was created, but PR exposure failed", processing)
        final_marker = "# Final mutable observation: serialize immediately after this exact causal sequence."
        self.assertLess(
            terminal.index('python3 -B scripts/issue_agent/validate.py "$root"'),
            terminal.index(final_marker),
        )
        self.assertLess(
            terminal.index(final_marker),
            terminal.index("> /tmp/CANDIDATE_VERIFICATION_RECEIPT.json"),
        )
        self.assertLess(
            terminal.index("/tmp/ci-jobs-emission.json)\" -eq 1"),
            terminal.index(final_marker),
        )
        self.assertGreater(
            terminal.rindex("pulls/$PR_NUMBER/reviews?per_page=100"),
            terminal.index(final_marker),
        )
        self.assertGreater(
            terminal.rindex("reviewThreads(first:100)"),
            terminal.index(final_marker),
        )

    def test_policy_and_owner_delegation_are_active_and_fail_closed(self):
        policy = json.loads((ROOT / "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json").read_text())
        delegation = json.loads((ROOT / "state/authorization/delegations/OWNER_REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json").read_text())
        continuation = json.loads((ROOT / "state/authorization/delegations/OWNER_AUTONOMOUS_REPOSITORY_CONTINUATION_V2.json").read_text())
        self.assertEqual(policy["schema"], "qikvrt_requested_review_and_issue_lifecycle_policy_v1")
        self.assertEqual(policy["status"], "ACTIVE")
        self.assertEqual(policy["issue_lifecycle"]["unclassified_open_issue"], "FORBIDDEN")
        self.assertEqual(delegation["state"], "ACTIVE")
        self.assertFalse(policy["mandatory_boundaries"]["merge_or_promotion_implicitly_authorized"])
        self.assertFalse(policy["mandatory_boundaries"]["external_publication_or_submission_authorized"])
        self.assertIn(
            "state/authorization/delegations/OWNER_REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json",
            continuation["related_delegations"],
        )

    def test_issue_agent_prompt_requires_one_lifecycle_disposition(self):
        for token in (
            "EXECUTE_NOW",
            "CLARIFICATION_REQUIRED",
            "BLOCKED_WITH_NEXT_ACTION",
            "CLOSE_COMPLETED",
            "CLOSE_NOT_PLANNED",
            "CLOSE_INVALID_OR_UNSUPPORTED",
        ):
            self.assertIn(token, SYSTEM_PROMPT)
        self.assertIn("Do not leave an issue in an unclassified waiting state", SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
