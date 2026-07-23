# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

PYTHON ?= python3
CC ?= cc
EFFECT_ACK_C90_CFLAGS ?= -std=c90 -pedantic -Wall -Wextra -Werror

.PHONY: test compile effect-ack-core-compile effect-ack-core-test scientific-bundle-test adaptive-cognition-test runtime-contract tool-cache-contract release-automation launcher unit conformance security license seed e2e integrity run-api clean

compile: effect-ack-core-compile
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m py_compile qikvrt.py tools/qikvrt_runtime_logger.py tools/qikvrt_subprocess.py tools/qikvrt_initial_acceptance_gate.py tools/qikvrt_integrity.py tools/qikvrt_tool_cache.py tools/qikvrt_master_acceptance_gate.py tools/qikvrt_cicd_publish.py tools/qikvrt_seed_common.py tools/qikvrt_validate_state_run.py tools/qikvrt_zenodo_actions.py tools/qikvrt_formalization_v2_zenodo.py tools/qikvrt_build_zenodo_manifest.py tools/qikvrt_status_zenodo.py src/qikvrt_effect_ack.py src/qikvrt_api_handler.py src/qikvrt_github_api_shim.py scripts/qikvrt_api_client.py tests/test_integrity.py tests/test_launcher_runtime.py tests/test_effect_ack_conformance.py tests/test_effect_ack_release_workflows.py tests/test_formalization_v2_release_workflow.py tests/test_formalization_v2_zenodo.py tests/test_status_release_workflows.py tests/test_zenodo_actions.py tests/test_status_zenodo.py tests/test_zenodo_manifest_builder.py tests/test_status_clarification_bundle.py tests/test_handler_unit.py tests/test_handler_security.py tests/test_api_client.py tests/test_license_transition.py tests/test_ietf_offline_render.py tests/test_seed_workflows.py tests/test_tcpip_e2e.py

effect-ack-core-compile:
	$(CC) $(EFFECT_ACK_C90_CFLAGS) -Iinclude -fsyntax-only src/effect_ack_core.c tests/test_effect_ack_core.c

effect-ack-core-test: effect-ack-core-compile
	CC="$(CC)" sh tests/test_effect_ack_core.sh

scientific-bundle-test:
	PYTHON="$(PYTHON)" sh tests/test_effect_ack_scientific_bundle.sh

adaptive-cognition-test:
	bash -n tools/qikvrt_adaptive_runtime.sh tests/test_adaptive_runtime.sh
	bash tests/test_adaptive_runtime.sh

tool-cache-contract:
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B tools/qikvrt_tool_cache.py verify

runtime-contract: tool-cache-contract
	sh -n tools/bootstrap-gh.sh tools/bootstrap-runtime.sh
	sh -n tests/test_runtime_bootstrap.sh
	sh tools/bootstrap-gh.sh --help >/dev/null
	sh tools/bootstrap-runtime.sh --help >/dev/null
	PYTHON="$(PYTHON)" sh tests/test_runtime_bootstrap.sh

release-automation:
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B -m unittest -v tests.test_effect_ack_release_workflows tests.test_formalization_v2_release_workflow tests.test_formalization_v2_zenodo tests.test_status_release_workflows tests.test_zenodo_actions tests.test_status_zenodo tests.test_zenodo_manifest_builder tests.test_status_clarification_bundle

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
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest -v tests.test_handler_security tests.test_api_client

license:
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B -m unittest -v tests.test_license_transition

seed:
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B -m unittest -v tests.test_seed_workflows
	@for script in tools/qikvrt_seed_*.sh; do sh -n "$$script"; done

e2e:
	$(PYTHON) tests/test_tcpip_e2e.py

test: compile integrity effect-ack-core-test scientific-bundle-test adaptive-cognition-test runtime-contract release-automation launcher conformance unit security license seed e2e
	PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 $(PYTHON) -B tools/qikvrt_integrity.py verify

run-api:
	@test -n "$(QIKVRT_API_TOKEN)" || (echo "BLOCK: set QIKVRT_API_TOKEN" >&2; exit 2)
	@test -n "$(QIKVRT_API_TOKEN_EXPIRES_UTC)" || (echo "BLOCK: set QIKVRT_API_TOKEN_EXPIRES_UTC" >&2; exit 2)
	@test -n "$(QIKVRT_ALLOWED_REPOSITORY)" || (echo "BLOCK: set QIKVRT_ALLOWED_REPOSITORY=owner/repo" >&2; exit 2)
	@test -n "$(QIKVRT_API_PRINCIPAL)" || (echo "BLOCK: set QIKVRT_API_PRINCIPAL" >&2; exit 2)
	PYTHONNOUSERSITE=1 $(PYTHON) -S src/qikvrt_github_api_shim.py

clean:
	rm -rf unit_state e2e_state .qikvrt/runtime .qikvrt/evidence .qikvrt/api .qikvrt/cache .qikvrt/release logs __pycache__ src/__pycache__ scripts/__pycache__ tests/__pycache__ tools/__pycache__
