# Test inventory

The 2026-07-22 EFFECT_ACK-universality release discovers twelve executable
Python test modules and runs 128 tests. The command-line offline-render checker
and the C90/shell gates are exercised separately by `make test`.

| Module | Tests |
|---|---:|
| `tests/test_api_client.py` | 4 |
| `tests/test_effect_ack_conformance.py` | 41 |
| `tests/test_handler_security.py` | 17 |
| `tests/test_handler_unit.py` | 6 |
| `tests/test_integrity.py` | 1 |
| `tests/test_launcher_runtime.py` | 15 |
| `tests/test_license_transition.py` | 5 |
| `tests/test_seed_workflows.py` | 12 |
| `tests/test_tcpip_e2e.py` | 1 |
| `tests/test_effect_ack_release_workflows.py` | 7 |
| `tests/test_zenodo_actions.py` | 17 |
| `tests/test_zenodo_manifest_builder.py` | 2 |
| **Total** | **128** |

The complete gate is:

```bash
make test
```

It also performs strict ANSI-C90 compilation and exhaustive model comparison,
scientific-proof regeneration, adaptive-runtime controls, active Python and
shell syntax checks, workflow and OpenAPI YAML parsing, JSON parsing,
license-transition verification, and canonical integrity verification. Static
gates and executable unit/end-to-end tests remain distinct even though
`make test` runs them as one verification path.

The local result is reference conformance, not production certification. The
corresponding hosted release evidence is retained on the public
`qikvrt/zenodo-state` branch after exact-tree CI and finalization.
