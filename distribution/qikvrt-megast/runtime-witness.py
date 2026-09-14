#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Guest-side observation after graphical login, transport and real execution."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import threading
import time
import traceback
import urllib.request

ROOT = Path("/opt/qikvrt")
LAST_STAGE = "initialization"


def stage(name):
    global LAST_STAGE
    LAST_STAGE = name
    subprocess.run(["logger", "-t", "qikvrt-runtime", "QIKVRT_RUNTIME_STEP " + name], check=True)


def run(command):
    return subprocess.run(command, capture_output=True, text=True, check=True, timeout=90).stdout


def main():
    config = json.loads(Path("/etc/qikvrt/distribution.json").read_text())
    source = config["source_sha"]
    stage("source=" + source)
    spec = importlib.util.spec_from_file_location("qikvrt_boot", ROOT / "boot.py")
    boot = importlib.util.module_from_spec(spec); spec.loader.exec_module(boot)
    # The graphical session invokes this witness; an early systemd marker cannot satisfy it.
    run(["pgrep", "-u", str(os.getuid()), "xfce4-session"])
    stage("xfce-session-observed")
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        windows = run(["xwininfo", "-root", "-tree"])
        if "Firefox" in windows:
            break
        time.sleep(1)
    else:
        raise RuntimeError("Firefox window was not mapped in the Xfce display")
    run(["pgrep", "-u", str(os.getuid()), "firefox-esr"])
    stage("firefox-window-observed")
    with urllib.request.urlopen("http://127.0.0.1:8771/.well-known/effect-ack", timeout=5) as response:
        capabilities = json.loads(response.read())
        if not capabilities:
            raise RuntimeError("empty Effect-Ack capability response")
    stage("effect-ack-http-observed")
    c90 = run(["/usr/local/bin/qikvrt-c90-selftest"])
    if "7864387" not in c90:
        raise RuntimeError("complete C90 corpus was not executed")
    stage("c90-corpus-observed")
    image = (ROOT / "runtime/QIKVRT_BOOT.BIN").read_bytes()
    with tempfile.TemporaryDirectory(prefix="qikvrt-guest-") as tmp:
        work = Path(tmp)
        with boot.BootDatagramServer(("127.0.0.1", 0), image) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            received = work / "QIKVRT_BOOT.BIN"
            try:
                transfer = run(["/usr/local/bin/qikvrt-boot-receive", "127.0.0.1", str(server.server_address[1]),
                                str(received), hashlib.sha256(image).hexdigest(), str(secrets.randbelow(0xfffffffe) + 1)])
            finally:
                server.shutdown(); thread.join()
        if received.read_bytes() != image:
            raise RuntimeError("received MC68000 program differs")
        stage("ip-program-received-and-hashed")
        received.chmod(0o700)
        m68k = run(["qemu-m68k", str(received)])
        if "ARCH=MC68000_FAMILY" not in m68k:
            raise RuntimeError("received MC68000 program did not execute")
        stage("received-m68000-program-executed")
        for file in (ROOT / "smalltalk").iterdir():
            if file.suffix in (".image", ".changes", ".sources"):
                shutil.copyfile(file, work / file.name)
        smalltalk = run([str(ROOT / "pharo-vm/bin/pharo"), "--headless", str(work / "QIKVRT.image"), "st", str(ROOT / "smalltalk/smoke.st")])
        if "QIKVRT_SMALLTALK_IMAGE_RESTORED" not in smalltalk:
            raise RuntimeError("Smalltalk image did not restore")
        stage("smalltalk-image-restored")
    receipt = {"schema": "qikvrt_megast_runtime_receipt_v1", "source_sha": source,
               "graphical_session": "Xfce with mapped Firefox window", "effect_ack_http_readback": True,
               "c90_checks": 7864387, "ip_boot_binary_sha256": hashlib.sha256(image).hexdigest(),
               "received_mc68000_executed": True, "smalltalk_image_restored": True,
               "physical_atari_boot": False, "effect_ack_done": False}
    Path.home().joinpath(".config/qikvrt/runtime-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    # Journal stream is forwarded to ttyS0 by the distribution's rsyslog rule.
    subprocess.run(["logger", "-t", "qikvrt-runtime", "QIKVRT_MEGAST_RUNTIME_OK source_sha=" + source], check=True)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        traceback.print_exc()
        detail = str(error) + " " + str(getattr(error, "stderr", ""))
        subprocess.run(["logger", "-t", "qikvrt-runtime", "QIKVRT_RUNTIME_BLOCK stage=" + LAST_STAGE + " error=" + detail[:2000]], check=False)
        raise SystemExit(1)
