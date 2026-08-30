# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

PYTHON ?= python3
CC ?= cc
EFFECT_ACK_C90_CFLAGS ?= -std=c90 -pedantic -Wall -Wextra -Werror

.PHONY: test compile effect-ack-core-compile effect-ack-core-test scientific-bundle-test adaptive-cognition-test anticipation-contract runtime-contract tool-cache-contract ai-runtime-contract interaction-archive-test release-automation evidence-contract-test m68000-kernel-contract workflow-executor-mesh-contract repository-terminal-test mesh-authority-mirror-instance-test real-mesh-test real-mesh-system-verification launcher unit conformance security license seed e2e integrity run-api clean

compile: effect-ack-core-compile
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m py_compile qikvrt.py tools/qikvrt_runtime_logger.py tools/qikvrt_subprocess.py tools/qikvrt_initial_acceptance_gate.py tools/qikvrt_integrity.py tools/qikvrt_tool_cache.py tools/ai_runtime_bootloader.py tools/qikvrt_master_acceptance_gate.py tools/qikvrt_cicd_publish.py tools/qikvrt_seed_common.py tools/qikvrt_workflow_executor.py tools/qikvrt_anticipation.py tools/qikvrt_validate_state_run.py tools/qikvrt_zenodo_actions.py tools/qikvrt_zenodo_metadata_edit.py tools/qikvrt_formalization_v2_zenodo.py tools/qikvrt_build_zenodo_manifest.py tools/qikvrt_status_zenodo.py tools/qikvrt_interaction_archive.py tools/qikvrt_global_completion.py tools/qikvrt_canonical_temporal_memory_kernel_evidence.py tools/qikvrt_vrtcore_zenodo_candidate.py tools/qikvrt_content_disposition_batch_001.py tools/qikvrt_content_disposition_batch_002_terminal.py tools/qikvrt_content_disposition_batch_002_corrected_candidate.py tools/qikvrt_content_disposition_batch_002_owner_acceptance.py tools/qikvrt_content_disposition_status_after_batch_002_acceptance.py tools/qikvrt_content_disposition_status_after_batch_002_acceptance_compat.py tools/qikvrt_content_disposition_batch_003_dispatch.py tools/qikvrt_zenodo_union_disposition.py tools/qikvrt_virtual_mesh_m68000_acceptance.py tools/qikvrt_authority_mirror_mesh_instance.py tools/qikvrt_real_mesh.py release/observer-relative-retrocausality-current-synthesis-zenodo-v2/finalize_authorized_controls.py src/qikvrt_effect_ack.py src/qikvrt_api_handler.py src/qikvrt_github_api_shim.py scripts/qikvrt_api_client.py tests/test_integrity.py tests/test_ai_runtime_bootloader.py tests/test_launcher_runtime.py tests/test_effect_ack_conformance.py tests/test_effect_ack_release_workflows.py tests/test_formalization_v2_release_workflow.py tests/test_formalization_v2_zenodo.py tests/test_status_release_workflows.py tests/test_zenodo_actions.py tests/test_zenodo_metadata_clarification_candidates.py tests/test_qikvrt_zenodo_metadata_edit.py tests/test_status_zenodo.py tests/test_zenodo_manifest_builder.py tests/test_status_clarification_bundle.py tests/test_global_completion.py tests/test_content_disposition_batch_001.py tests/test_content_disposition_batch_002_terminal.py tests/test_content_disposition_batch_002_corrected_candidate.py tests/test_content_disposition_batch_002_owner_acceptance.py tests/test_content_disposition_status_after_batch_002_acceptance.py tests/test_content_disposition_batch_003_dispatch.py tests/test_zenodo_union_disposition.py tests/test_handler_unit.py tests/test_handler_security.py tests/test_api_client.py tests/test_interaction_archive.py tests/test_anticipation.py tests/test_license_transition.py tests/test_ietf_offline_render.py tests/test_seed_workflows.py tests/test_qikvrt_workflow_executor_mesh_contract.py tests/test_qikvrt_autonomous_pr_head_continuation.py tests/test_qikvrt_pr_head_recovery.py tests/test_qikvrt_virtual_mesh_m68000_acceptance.py tests/test_tcpip_e2e.py tests/test_canonical_temporal_memory_publication.py tests/test_qikvrt_authority_mirror_mesh_instance.py tests/test_qikvrt_real_mesh.py tools/qikvrt_real_mesh_system_verification.py tests/test_qikvrt_real_mesh_system_verification.py

effect-ack-core-compile:
	$(CC) $(EFFECT_ACK_C90_CFLAGS) -Iinclude -fsyntax-only src/effect_ack_core.c tests/test_effect_ack_core.c

effect-ack-core-test: effect-ack-core-compile
	CC="$(CC)" sh tests/test_effect_ack_core.sh

scientific-bundle-test:
	PYTHON="$(PYTHON)" sh tests/test_effect_ack_scientific_bundle.sh

adaptive-cognition-test:
	bash -n tools/qikvrt_adaptive_runtime.sh tests/test_adaptive_runtime.sh
	bash tests/test_adaptive_runtime.sh

anticipation-contract:
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B -m unittest -v tests.test_anticipation
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B tools/qikvrt_anticipation.py check >/dev/null

tool-cache-contract:
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B tools/qikvrt_tool_cache.py verify

runtime-contract: tool-cache-contract
	sh -n tools/bootstrap-gh.sh tools/bootstrap-runtime.sh
	sh -n tests/test_runtime_bootstrap.sh
	sh tools/bootstrap-gh.sh --help >/dev/null
	sh tools/bootstrap-runtime.sh --help >/dev/null
	PYTHON="$(PYTHON)" sh tests/test_runtime_bootstrap.sh

ai-runtime-contract:
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B -m unittest -v tests.test_ai_runtime_bootloader
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B tools/ai_runtime_bootloader.py --help >/dev/null

interaction-archive-test:
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B -m unittest -v tests.test_interaction_archive
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B tools/qikvrt_interaction_archive.py --help >/dev/null

release-automation:
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B -m unittest -v tests.test_effect_ack_release_workflows tests.test_formalization_v2_release_workflow tests.test_formalization_v2_zenodo tests.test_status_release_workflows tests.test_zenodo_actions tests.test_zenodo_metadata_clarification_candidates tests.test_qikvrt_zenodo_metadata_edit tests.test_status_zenodo tests.test_zenodo_manifest_builder tests.test_status_clarification_bundle tests.test_global_completion tests.test_content_disposition_batch_002_terminal tests.test_content_disposition_batch_002_corrected_candidate tests.test_content_disposition_batch_002_owner_acceptance tests.test_content_disposition_status_after_batch_002_acceptance tests.test_content_disposition_batch_003_dispatch tests.test_transactional_workflow_trigger
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B tests/test_content_disposition_batch_001.py
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B tests/test_zenodo_union_disposition.py

evidence-contract-test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m py_compile tools/qikvrt_zenodo_publish.py tools/qikvrt_zenodo_corpus_proof.py tools/qikvrt_zenodo_machine_proof.py tools/qikvrt_vrtcore_zenodo_publication_controls.py release/observer-relative-retrocausality-current-synthesis-zenodo-v2/finalize_authorized_controls.py tools/qikvrt_canonical_temporal_memory_kernel_evidence.py tools/qikvrt_continuation_ledger.py scripts/issue_agent/continuation.py scripts/issue_agent/validate.py tests/issue_agent/test_continuation.py tests/issue_agent/test_validate.py tests/test_qikvrt_continuation_ledger.py tests/test_authority_mirror_equality_receipt.py tests/test_canonical_closing_status_article.py tests/test_charter_zenodo.py tests/test_qikvrt_self_disclosure.py tests/test_qikvrt_quantitative_comparison_publication.py tests/test_planck_spacetime_unit_quantum_tunnel_publication.py tests/test_virtual_past_reception.py tests/test_quantum_classical_runtime_article.py tests/test_canonical_temporal_memory_publication.py tests/test_vrtcore_h56_zenodo_candidate.py tests/test_vrtcore_zenodo_publication_controls.py tests/test_observer_relative_retrocausality_zenodo_finalizer.py tests/test_zenodo_corpus_inventory_failure_receipt.py tests/test_zenodo_corpus_proof.py tests/test_zenodo_machine_proof_policy.py
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B tools/qikvrt_canonical_temporal_memory_kernel_evidence.py --static-only >/dev/null
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B -m unittest -v tests.issue_agent.test_continuation tests.issue_agent.test_validate tests.test_qikvrt_continuation_ledger tests.test_authority_mirror_equality_receipt tests.test_canonical_closing_status_article tests.test_charter_zenodo tests.test_qikvrt_self_disclosure tests.test_qikvrt_quantitative_comparison_publication tests.test_planck_spacetime_unit_quantum_tunnel_publication tests.test_virtual_past_reception tests.test_quantum_classical_runtime_article tests.test_canonical_temporal_memory_publication tests.test_vrtcore_h56_zenodo_candidate tests.test_vrtcore_zenodo_publication_controls tests.test_observer_relative_retrocausality_zenodo_finalizer tests.test_zenodo_corpus_inventory_failure_receipt tests.test_zenodo_corpus_proof tests.test_zenodo_machine_proof_policy

m68000-kernel-contract:
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B -m unittest -v tests.test_qikvrt_virtual_mesh_m68000_acceptance
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B tools/qikvrt_virtual_mesh_m68000_acceptance.py --iterations 3 --json >/dev/null

workflow-executor-mesh-contract: m68000-kernel-contract
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B -m unittest -v tests.test_qikvrt_workflow_executor_mesh_contract tests.test_qikvrt_continuation_ledger tests.test_qikvrt_reflexive_repository_watchdog tests.test_qikvrt_autonomous_pr_head_continuation tests.test_qikvrt_pr_head_recovery tests.test_qikvrt_native_account_review tests.test_seed_workflows
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B tools/qikvrt_workflow_executor.py snapshot --expect-head "$$(git rev-parse --verify HEAD^{commit})" --json >/dev/null

repository-terminal-test:
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B -m unittest -v tests.test_qikvrt_repository_terminal

mesh-authority-mirror-instance-test:
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B -m unittest -v tests.test_qikvrt_authority_mirror_mesh_instance

real-mesh-test:
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B -m unittest -v tests.test_qikvrt_real_mesh

real-mesh-system-verification:
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B -m unittest -v tests.test_qikvrt_real_mesh_system_verification

integrity:
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B tests/test_integrity.py
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B tools/qikvrt_integrity.py verify

launcher:
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B tests/test_launcher_runtime.py

unit:
	$(PYTHON) tests/test_handler_unit.py

conformance:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest -v tests.test_effect_ack_conformance

security:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B -m unittest -v tests.test_handler_security tests.test_api_client

license:
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B -m unittest -v tests.test_license_transition

seed:
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B -m unittest -v tests.test_seed_workflows
	@for script in tools/qikvrt_seed_*.sh; do sh -n "$$script"; done

e2e:
	$(PYTHON) tests/test_tcpip_e2e.py

test: compile integrity effect-ack-core-test scientific-bundle-test adaptive-cognition-test anticipation-contract runtime-contract ai-runtime-contract interaction-archive-test release-automation evidence-contract-test workflow-executor-mesh-contract repository-terminal-test mesh-authority-mirror-instance-test real-mesh-test real-mesh-system-verification launcher conformance unit security license seed e2e
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B tools/qikvrt_integrity.py verify

run-api:
	@test -n "$(QIKVRT_API_TOKEN)" || (echo "BLOCK: set QIKVRT_API_TOKEN" >&2; exit 2)
	@test -n "$(QIKVRT_API_TOKEN_EXPIRES_UTC)" || (echo "BLOCK: set QIKVRT_API_TOKEN_EXPIRES_UTC" >&2; exit 2)
	@test -n "$(QIKVRT_ALLOWED_REPOSITORY)" || (echo "BLOCK: set QIKVRT_ALLOWED_REPOSITORY=owner/repo" >&2; exit 2)
	@test -n "$(QIKVRT_API_PRINCIPAL)" || (echo "BLOCK: set QIKVRT_API_PRINCIPAL" >&2; exit 2)
	PYTHONNOUSERSITE=1 $(PYTHON) -S src/qikvrt_github_api_shim.py

clean:
	rm -rf unit_state e2e_state .qikvrt/runtime .qikvrt/evidence .qikvrt/api .qikvrt/cache .qikvrt/release .qikvrt/interactions .qikvrt/real-mesh logs __pycache__ src/__pycache__ scripts/__pycache__ tests/__pycache__ tools/__pycache__
