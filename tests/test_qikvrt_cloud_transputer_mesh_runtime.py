from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit

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


class _MeshLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.append(dict(attrs)["href"])


def _mesh_links():
    parser = _MeshLinks()
    parser.feed((ROOT / "deploy/universal-terminal/mesh-index.html").read_text())
    return parser.links


def test_ai_gateway_routes_reuse_the_live_mesh_surface():
    nginx = (ROOT / "deploy/universal-terminal/nginx.conf").read_text()
    assert "absolute_redirect off;" in nginx
    for path in ("/", "/AI"):
        block = nginx.split(f"location = {path} {{", 1)[1].split("}", 1)[0]
        assert "return 308 /AI/;" in block
    block = nginx.split("location = /AI/ {", 1)[1].split("}", 1)[0]
    assert "try_files /mesh-index.html =404;" in block
    assert 'add_header Cache-Control "no-store" always;' in block
    assert "return 200" not in block


def test_ai_and_legacy_mesh_routes_resolve_the_same_live_targets():
    expected = {
        "/qik-vrt/mesh/v1/terminal/vnc.html",
        "/qik-vrt/mesh/v1/effect-ack/.well-known/effect-ack",
        "/qik-vrt/mesh/v1/effect-ack/terminal/state",
        "/qik-vrt/mesh/v1/healthz",
    }
    for base in ("https://runtime.example/AI/", "https://runtime.example/qik-vrt/mesh/v1/"):
        resolved = [urlsplit(urljoin(base, link)) for link in _mesh_links()]
        assert {target.path for target in resolved} == expected
        assert all(target.scheme == "https" and target.netloc == "runtime.example" for target in resolved)


def test_firefox_launcher_binds_the_bookworm_novnc_websocket_path():
    target = next(urlsplit(link) for link in _mesh_links() if "vnc.html" in link)
    settings = parse_qs(target.query)
    assert settings["path"] == ["qik-vrt/mesh/v1/terminal/websockify"]
    # noVNC 1.3 constructs scheme://host:port/ + path; the default would be
    # /websockify and miss the gateway's nested terminal location entirely.
    websocket_path = "/" + settings["path"][0]
    assert websocket_path == "/qik-vrt/mesh/v1/terminal/websockify"
    assert settings["autoconnect"] == ["true"]
    assert settings["resize"] == ["scale"]
    assert settings["reconnect"] == ["false"]
    assert not {"password", "token", "host", "port"}.intersection(settings)


def test_ai_surface_does_not_assert_a_personal_session_or_completed_work():
    surface = (ROOT / "deploy/universal-terminal/mesh-index.html").read_text()
    assert "operator session" in surface
    assert "not a per-visitor isolated browser" in surface
    assert "not a productive continuation receipt" in surface
    assert "does not itself assert" in surface
    assert "EFFECT_ACK_DONE" in surface
    assert "setInterval" not in surface
    assert "http-equiv=\"refresh\"" not in surface
