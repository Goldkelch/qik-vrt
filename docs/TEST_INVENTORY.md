# Test inventory

The fixed 2026-07-20 release discovers nine executable test modules and runs
102 tests.

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
| **Total** | **102** |

The complete gate is:

```bash
make test
```

It also performs active Python and shell syntax checks, workflow and OpenAPI
YAML parsing, JSON parsing, license-transition verification, canonical
integrity verification, and a final tracked-diff check. Static gates and
executable unit/end-to-end tests remain distinct even though `make test` runs
them as one verification path.

The local result is reference conformance, not production certification. The
corresponding hosted test job for the fixed release completed successfully in
[GitHub Actions run 29764193906](https://github.com/Goldkelch/qik-vrt/actions/runs/29764193906).
