from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cloud_carrier_materializes_transputer_mesh_roles():
    script = (ROOT / "deploy/universal-terminal/cloud-entrypoint.sh").read_text()
    for mode in ("m68k", "smtpd", "dnsd", "snmpd"):
        assert f"QIKVRT_SERVICE_MODE={mode}" in script
    assert "qikvrt_cloud_transputer_mesh_health_v1" in script
    assert "effect_ack\":\"NOT_IMPLIED" in script
    assert "emit_health READY" in script


def test_mesh_health_is_a_runtime_readback_not_static_success():
    nginx = (ROOT / "deploy/universal-terminal/nginx.conf").read_text()
    assert "alias /tmp/qikvrt-mesh-health.json;" in nginx
    assert "location = /qik-vrt/mesh/v1/healthz" in nginx
    assert "location = /qik-vrt/mesh/v1/topology" in nginx
    assert "return 200" not in nginx.split("location = /qik-vrt/mesh/v1/healthz", 1)[1].split("}", 1)[0]

def test_compose_gateway_health_waits_for_real_terminal_endpoints():
    service = (ROOT / "deploy/universal-terminal/service-entrypoint.sh").read_text()
    assert "qikvrt_compose_mesh_gateway_health_v1" in service
    assert "http://127.0.0.1:8771/.well-known/effect-ack" in service
    assert "http://127.0.0.1:6080/vnc.html" in service
    assert '"terminal":"OBSERVED"' in service
    assert '"m68k":"SEPARATELY_REOBSERVED"' in service
    assert '"effect_ack":"NOT_IMPLIED"' in service
