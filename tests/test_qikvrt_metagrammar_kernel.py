from copy import deepcopy

from tools.qikvrt_metagrammar_kernel import validate


def valid_message():
    return {
        "protocol": "QMV/1.0",
        "AUTHORITY": {
            "repository": "Goldkelch/qik-vrt",
            "ref": "refs/heads/main",
            "head": "a" * 40,
            "tree": "b" * 40,
        },
        "SUCCESSOR_BINDING": {"head": "c" * 40, "tree": "d" * 40},
        "MATERIALIZATION": {"state": "VERIFIED"},
        "EXACT_HEAD_GATES": {
            "head": "c" * 40,
            "all_applicable_executed_terminal_success": True,
            "action_required": False,
            "zero_job": False,
        },
        "INWARD_REFLEXIVITY": {
            "productive_writer_admitted": True,
            "observer_admitted": True,
        },
        "OUTWARD_REFLECTION": {
            "completion": {"PASS": True, "FINAL_PASS": False, "EFFECT_ACK_DONE": False}
        },
        "FIRST_DETERMINISTIC_BLOCKER": "NONE",
        "NEXT_ACTION": "OBSERVE_OR_PROMOTE_UNDER_EXACT_AUTHORIZATION",
        "effects": {"transport_ack": False, "effect_ack": False},
    }


def test_valid_message_is_accepted():
    assert validate(valid_message()) == []


def test_final_pass_requires_pass():
    message = valid_message()
    message["OUTWARD_REFLECTION"]["completion"] = {
        "PASS": False,
        "FINAL_PASS": True,
        "EFFECT_ACK_DONE": False,
    }
    assert "QMV-E011" in validate(message)


def test_effect_ack_done_requires_final_pass():
    message = valid_message()
    message["OUTWARD_REFLECTION"]["completion"] = {
        "PASS": True,
        "FINAL_PASS": False,
        "EFFECT_ACK_DONE": True,
    }
    assert "QMV-E012" in validate(message)


def test_action_required_cannot_be_success():
    message = valid_message()
    message["EXACT_HEAD_GATES"]["action_required"] = True
    assert "QMV-E007" in validate(message)


def test_blocker_closes_productive_writer():
    message = valid_message()
    message["FIRST_DETERMINISTIC_BLOCKER"] = "INTEGRITY_FAILURE"
    assert "QMV-E-FAIL-CLOSED" in validate(message)


def test_transport_ack_is_not_effect_ack():
    message = valid_message()
    message["effects"] = {"transport_ack": True, "effect_ack": False}
    message["OUTWARD_REFLECTION"]["completion"]["EFFECT_ACK_DONE"] = True
    errors = validate(message)
    assert "QMV-E009" in errors
    assert "QMV-E012" in errors


def test_missing_section_is_rejected():
    message = deepcopy(valid_message())
    del message["MATERIALIZATION"]
    assert "QMV-E-MISSING-MATERIALIZATION" in validate(message)
