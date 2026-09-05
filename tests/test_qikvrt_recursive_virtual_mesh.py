import importlib.util
from pathlib import Path

MODULE = Path(__file__).parents[1] / "tools" / "qikvrt_recursive_virtual_mesh.py"
spec = importlib.util.spec_from_file_location("virtual_mesh", MODULE)
virtual_mesh = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(virtual_mesh)

def test_virtual_mesh_is_deterministic_and_fail_closed():
    parent = {
        "authority_repository": "Goldkelch/qik-vrt",
        "authority_head": "a" * 40,
        "authority_tree": "b" * 40,
        "blocker": "REQUESTED_REVIEW_EXECUTION_PENDING",
    }
    first = virtual_mesh.create_virtual_mesh(parent)
    second = virtual_mesh.create_virtual_mesh(parent)
    assert first["instance_id"] == second["instance_id"]
    assert first["role"] == "VIRTUAL_AUTHORITY"
    assert first["authority_rules"]["post_dispatch_deep_reobservation"] == "REQUIRED"
    assert first["authority_rules"]["predecessor_evidence_transfer"] == "FORBIDDEN"
    assert first["completion"]["final_pass"] is False
    assert "WORKFLOW_RUNS_JOBS_STEPS_CHECKS_AND_ARTIFACTS" in first["required_deep_reobservation"]

def test_virtual_mesh_rejects_unbound_parent():
    try:
        virtual_mesh.create_virtual_mesh({"authority_repository": "Goldkelch/qik-vrt"})
    except ValueError as error:
        assert "authority_head" in str(error)
    else:
        raise AssertionError("missing parent binding must fail closed")
