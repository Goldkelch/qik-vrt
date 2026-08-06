        print_json(
            {
                "schema": "qikvrt_autonomous_orchestrator_error_v2",
                "state": "BLOCK",
                "failure_class": "AUTONOMOUS_ORCHESTRATOR_BLOCKED",
                "detail": str(exc),
                "external_effect": "NONE",
                "completion_claims": {
                    "PASS": False,
                    "FINAL_PASS": False,
                    "EFFECT_ACK_DONE": False,
                },
            }
        )
        return 2
    print_json(result)
    if result.get("state", "").startswith("BLOCKED"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
