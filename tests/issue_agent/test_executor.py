import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.issue_agent.binding import canonical_bytes
from scripts.issue_agent.executor import (
    CONTRACT_PATH,
    FALSE_CLAIMS,
    ExecutorBlock,
    build_execution_receipt,
    build_plan,
    load_contract,
    verify_existing_result,
)
from scripts.issue_agent.infer import deterministic_answer
from scripts.issue_agent.validate import section
from tests.issue_agent import test_validate as validation_helpers


ROOT = Path(__file__).resolve().parents[2]
AUTHORITY = validation_helpers.AUTHORITY
SOURCE_TIME = validation_helpers.SOURCE_TIME
write_sidecar = validation_helpers.write_sidecar
ROOT_MARKER = "<!-- qikvrt-root-blocker-repair-order-v1 -->\nExecute.\n"


class TypedIssueExecutorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.helper = validation_helpers.ValidateIssueAgentBundleTest(methodName="runTest")

    def make_root_bundle(self, directory: Path) -> dict:
        issue, request, policy, policy_sha256 = self.helper.make_request(
            directory, body=ROOT_MARKER
        )
        answer = deterministic_answer(issue, request, policy, policy_sha256)
        (directory / "ANSWER.md").write_text(answer, encoding="utf-8")
        status = {
            "schema": "qikvrt_issue_agent_status_v2",
            "status": "CONTINUE",
            "issue_materialized": True,
            "model_inference_completed": False,
            "deterministic_contract_completed": True,
            "evaluation_completed": True,
            "evaluation_mode": "DETERMINISTIC_OWNER_CONTRACT",
            "handler_id": section(answer, "Handler id"),
            "handler_sha256": section(answer, "Handler SHA-256"),
            "request_fingerprint": request["request_fingerprint"],
            "issue_disposition": "EXECUTE_NOW",
            "disposition_reason": section(answer, "Disposition reason"),
            "next_action": section(answer, "Required next action"),
            "closure_recommended": False,
            "automatic_issue_close": False,
            "automatic_merge": False,
            "mirror_sync_required": False,
            "common_tag_required": False,
            "generated_at": SOURCE_TIME,
            "no_false_pass": True,
            "claims": FALSE_CLAIMS,
        }
        (directory / "STATUS.json").write_text(
            json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        self.helper.refresh_evaluation(directory)
        self.helper.rebuild_reduction(directory)
        return request

    def make_receipt(
        self,
        directory: Path,
        *,
        mapped: bool = True,
        run_id: int = 700,
        attempt: int = 1,
        candidate_head: str = "4" * 40,
    ) -> Path:
        request = json.loads((directory / "REQUEST.json").read_text(encoding="utf-8"))
        status = json.loads((directory / "STATUS.json").read_text(encoding="utf-8"))
        contract, registry_sha256 = load_contract(ROOT)
        registered = next(
            (entry for entry in contract["handlers"] if entry["handler_id"] == status["handler_id"]),
            None,
        )
        if mapped:
            assert registered is not None
            entry_sha256 = hashlib.sha256(canonical_bytes(registered)).hexdigest()
            executor_id = registered["executor_id"]
            registration = "REGISTERED_EXACT_HEAD"
            handoff = "READY_FOR_EXACT_HEAD_EXECUTOR_DISPATCH"
            declared = contract["contract_id"]
        else:
            entry_sha256 = "UNMAPPED"
            executor_id = "UNMAPPED"
            registration = "NOT_REGISTERED_EXACT_HEAD"
            handoff = "HOLD_EXECUTOR_NOT_REGISTERED"
            declared = "UNREGISTERED"
        binding = request["binding"]
        receipt = {
            "schema": "qikvrt_issue_agent_work_admission_receipt_v2",
            "repository": AUTHORITY,
            "pull_request": 912,
            "head": candidate_head,
            "tree": "5" * 40,
            "current_main": binding["authority_head"],
            "request_fingerprint": request["request_fingerprint"],
            "candidate_class": "WORK_ADMISSION",
            "issue_disposition": "EXECUTE_NOW",
            "handler_id": status["handler_id"],
            "handler_sha256": status["handler_sha256"],
            "work_order_payload_sha256": binding["selected_body_sha256"],
            "declared_executor_contract": declared,
            "executor_registry_sha256": registry_sha256,
            "executor_entry_sha256": entry_sha256,
            "executor_controller_path": "scripts/issue_agent/executor.py",
            "executor_controller_blob_sha1": "6" * 40,
            "executor_workflow_path": ".github/workflows/issue-agent-executor.yml",
            "executor_workflow_blob_sha1": "7" * 40,
            "registered_executor_id": executor_id,
            "executor_registration_state": registration,
            "verifier_workflow_run_id": run_id,
            "verifier_workflow_run_attempt": attempt,
            "verifier_workflow_name": "Issue agent exact candidate verifier",
            "verifier_workflow_ref": (
                f"{AUTHORITY}/.github/workflows/issue-agent-autofinish.yml@refs/heads/main"
            ),
            "verifier_workflow_sha": binding["authority_head"],
            "verifier_workflow_blob_sha1": "8" * 40,
            "verifier_authority_tree": binding["authority_tree"],
            "review_required": False,
            "review_gate": "NOT_REQUIRED_FOR_WORK_ADMISSION",
            "pr_snapshot_sha256": "9" * 64,
            "reviews_sha256": "a" * 64,
            "threads_sha256": "b" * 64,
            "ci_run_id": 600,
            "ci_jobs_sha256": "c" * 64,
            "issue_agent_run_id": 500,
            "issue_agent_jobs_sha256": "d" * 64,
            "issue_reduction_artifact_id": 400,
            "state": handoff,
            "repository_content_effect": "NONE",
            "authority_lifecycle_effect": "NONE",
            "platform_transport_effects_declared": [
                "ACTIONS_ARTIFACT_UPLOAD", "ACTIONS_JOB_SUMMARY_WRITE"
            ],
            "claims": FALSE_CLAIMS,
        }
        transport = directory.parent / "transport"
        transport.mkdir(exist_ok=True)
        path = transport / "CANDIDATE_VERIFICATION_RECEIPT.json"
        path.write_bytes(canonical_bytes(receipt))
        write_sidecar(path)
        return path

    def plan(self, bundle: Path, receipt: Path) -> dict:
        return build_plan(
            bundle,
            receipt,
            root=ROOT,
            verify_authority=False,
            verify_candidate_git=False,
        )

    def test_registry_has_one_bounded_non_completion_handler(self):
        contract, digest = load_contract(ROOT)
        self.assertEqual(len(digest), 64)
        self.assertEqual(len(contract["handlers"]), 1)
        handler = contract["handlers"][0]
        self.assertEqual(handler["input_contract"], "FIXED_REGISTERED_HANDLER_DESCRIPTOR")
        self.assertFalse(handler["selected_body_controls_operations"])
        self.assertIn("NOT_REPAIR_COMPLETION", handler["work_product"])

    def test_registry_handler_digest_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / Path(CONTRACT_PATH).parent).mkdir(parents=True)
            (root / Path("policy/ISSUE_AGENT_DETERMINISTIC_INTAKE_V1.json").parent).mkdir(
                parents=True
            )
            shutil.copy2(ROOT / CONTRACT_PATH, root / CONTRACT_PATH)
            shutil.copy2(
                ROOT / "policy/ISSUE_AGENT_DETERMINISTIC_INTAKE_V1.json",
                root / "policy/ISSUE_AGENT_DETERMINISTIC_INTAKE_V1.json",
            )
            contract_path = root / CONTRACT_PATH
            value = json.loads(contract_path.read_text(encoding="utf-8"))
            value["handlers"][0]["handler_sha256"] = "0" * 64
            contract_path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(ExecutorBlock):
                load_contract(root)

    def test_registered_root_handler_builds_bounded_plan(self):
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp) / "bundle"
            self.make_root_bundle(bundle)
            plan = self.plan(bundle, self.make_receipt(bundle))
            self.assertEqual(plan["state"], "READY_TO_MATERIALIZE")
            self.assertEqual(plan["claims"], FALSE_CLAIMS)
            self.assertEqual(plan["authority_main_effect"], "NONE")
            self.assertEqual(len(plan["changed_paths"]), 2)

    def test_execution_receipt_is_attestation_not_repair_completion(self):
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp) / "bundle"
            self.make_root_bundle(bundle)
            plan = self.plan(bundle, self.make_receipt(bundle))
            receipt = build_execution_receipt(plan)
            self.assertEqual(receipt["claims"], FALSE_CLAIMS)
            self.assertFalse(receipt["candidate_code_executed"])
            self.assertEqual(receipt["authority_main_effect"], "NONE")
            self.assertEqual(
                receipt["work_product_sha256"],
                hashlib.sha256(canonical_bytes(receipt["work_product"])).hexdigest(),
            )

    def test_redelivery_run_identity_does_not_change_execution_id(self):
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp) / "bundle"
            self.make_root_bundle(bundle)
            first = self.plan(bundle, self.make_receipt(bundle, run_id=700, attempt=1))
            second = self.plan(bundle, self.make_receipt(bundle, run_id=701, attempt=2))
            self.assertEqual(first["execution_id"], second["execution_id"])
            self.assertNotEqual(
                first["admission_provenance"]["candidate_verification_receipt_sha256"],
                second["admission_provenance"]["candidate_verification_receipt_sha256"],
            )

    def test_existing_result_accepts_new_delivery_provenance_only(self):
        with tempfile.TemporaryDirectory() as temp:
            worktree = Path(temp)
            subprocess.run(["git", "init", "-q", str(worktree)], check=True)
            subprocess.run(["git", "-C", str(worktree), "config", "user.name", "test"], check=True)
            subprocess.run(["git", "-C", str(worktree), "config", "user.email", "test@example.invalid"], check=True)
            (worktree / "base").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(worktree), "add", "base"], check=True)
            subprocess.run(["git", "-C", str(worktree), "commit", "-qm", "base"], check=True)
            authority = subprocess.check_output(
                ["git", "-C", str(worktree), "rev-parse", "HEAD"], text=True
            ).strip()
            output_root = "evidence/issues/76/executions/fingerprint/execution"
            changed = sorted([
                f"{output_root}/EXECUTION_RECEIPT.json",
                f"{output_root}/EXECUTION_RECEIPT.sha256",
                "REPOSITORY_FILE_MANIFEST.json",
                "REPOSITORY_FILE_MANIFEST.json.sha256",
                "SHA256SUMS.txt",
            ])
            identity = {
                "schema": "qikvrt_issue_agent_execution_identity_v1",
                "authority_main": authority,
                "work_product_sha256": "1" * 64,
            }
            stable = {
                "verifier_workflow_name": "Issue agent exact candidate verifier",
                "verifier_workflow_ref": f"{AUTHORITY}/.github/workflows/issue-agent-autofinish.yml@refs/heads/main",
                "verifier_workflow_sha": authority,
                "verifier_workflow_blob_sha1": "2" * 40,
                "verifier_authority_tree": "3" * 40,
            }
            old_provenance = {
                **stable,
                "candidate_verification_receipt_sha256": "4" * 64,
                "verifier_workflow_run_id": 10,
                "verifier_workflow_run_attempt": 1,
            }
            plan = {
                "state": "READY_TO_MATERIALIZE",
                "authority_main": authority,
                "execution_identity": identity,
                "admission_provenance": old_provenance,
                "execution_id": "execution",
                "implementation": "ROOT_CONTROL_PLANE_ATTESTATION_V1",
                "output_root": output_root,
                "work_product": {"bounded_attestation": True},
                "allowed_candidate_paths": changed,
            }
            output = worktree / output_root
            output.mkdir(parents=True)
            receipt_path = output / "EXECUTION_RECEIPT.json"
            receipt_path.write_bytes(canonical_bytes(build_execution_receipt(plan)))
            write_sidecar(receipt_path)
            for name in (
                "REPOSITORY_FILE_MANIFEST.json",
                "REPOSITORY_FILE_MANIFEST.json.sha256",
                "SHA256SUMS.txt",
            ):
                (worktree / name).write_text(f"{name}\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(worktree), "add", "--", *changed], check=True)
            subprocess.run(["git", "-C", str(worktree), "commit", "-qm", "result"], check=True)
            new_plan = dict(plan)
            new_plan["admission_provenance"] = {
                **stable,
                "candidate_verification_receipt_sha256": "5" * 64,
                "verifier_workflow_run_id": 11,
                "verifier_workflow_run_attempt": 2,
            }
            with mock.patch("scripts.issue_agent.executor.build_plan", return_value=new_plan):
                result = verify_existing_result(Path("unused"), Path("unused"), worktree)
            self.assertEqual(result["state"], "VERIFIED_EXISTING_RESULT")

    def test_distinct_candidate_head_changes_execution_id(self):
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp) / "bundle"
            self.make_root_bundle(bundle)
            first = self.plan(bundle, self.make_receipt(bundle, candidate_head="4" * 40))
            second = self.plan(bundle, self.make_receipt(bundle, candidate_head="e" * 40))
            self.assertNotEqual(first["execution_id"], second["execution_id"])

    def test_unmapped_model_handler_returns_stable_hold(self):
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp) / "bundle"
            self.helper.make_bundle(bundle)
            receipt = self.make_receipt(bundle, mapped=False)
            plan = self.plan(bundle, receipt)
            self.assertEqual(plan["state"], "HOLD")
            self.assertEqual(plan["failure_class"], "UNMAPPED_HANDLER")
            self.assertEqual(plan["changed_paths"], [])

    def test_forged_dispatch_state_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp) / "bundle"
            self.make_root_bundle(bundle)
            receipt_path = self.make_receipt(bundle)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["executor_registration_state"] = "NOT_REGISTERED_EXACT_HEAD"
            receipt_path.write_bytes(canonical_bytes(receipt))
            write_sidecar(receipt_path)
            with self.assertRaises(ExecutorBlock):
                self.plan(bundle, receipt_path)

    def test_receipt_surplus_field_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            bundle = Path(temp) / "bundle"
            self.make_root_bundle(bundle)
            receipt_path = self.make_receipt(bundle)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["command"] = "echo candidate controlled"
            receipt_path.write_bytes(canonical_bytes(receipt))
            write_sidecar(receipt_path)
            with self.assertRaises(ExecutorBlock):
                self.plan(bundle, receipt_path)

    def test_workflow_is_event_driven_create_only_and_draft_only(self):
        text = (ROOT / ".github/workflows/issue-agent-executor.yml").read_text(encoding="utf-8")
        self.assertNotIn("schedule:", text)
        self.assertIn("workflow_run:", text)
        self.assertIn('issue-executor/$ISSUE_NUMBER/$EXECUTION_ID', text)
        self.assertIn('--force-with-lease="refs/heads/$branch:"', text)
        self.assertIn("--draft", text)
        self.assertNotIn("gh pr merge", text)
        self.assertNotIn("gh release", text)

    def test_candidate_code_is_never_invoked_by_workflow(self):
        text = (ROOT / ".github/workflows/issue-agent-executor.yml").read_text(encoding="utf-8")
        self.assertNotIn("/tmp/candidate-bundle/", "\n".join(
            line for line in text.splitlines() if "python" in line or "bash" in line
        ))
        self.assertIn("git show", text)
        self.assertIn("candidate_code_execution", (ROOT / CONTRACT_PATH).read_text())


if __name__ == "__main__":
    unittest.main()
