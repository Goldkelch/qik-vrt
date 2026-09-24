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
import sys
import tempfile
import threading
import time
import traceback
import urllib.request

ROOT = Path("/opt/qikvrt")
LAST_STAGE = "initialization"


def emit_serial(message):
    """Emit terminal runtime evidence on the host-observed channel directly."""
    line = message.rstrip("\n") + "\n"
    try:
        with open("/dev/ttyS0", "w") as serial:
            serial.write(line)
            serial.flush()
    except OSError:
        print(line, end="", flush=True)


def stage(name):
    global LAST_STAGE
    LAST_STAGE = name
    subprocess.run(["logger", "-t", "qikvrt-runtime", "QIKVRT_RUNTIME_STEP " + name], check=True)


def run(command):
    return subprocess.run(command, capture_output=True, text=True, check=True, timeout=90).stdout


def wait_for_window(name, timeout=90):
    """Require a complete window-tree observation within the startup deadline."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            windows = run(["xwininfo", "-root", "-tree"])
        except subprocess.CalledProcessError as error:
            # Xfce, Firefox and Hatari create/destroy windows concurrently with
            # xwininfo's traversal. A vanished drawable invalidates this entire
            # sample; only a later successful query can witness the window.
            errors = [line for line in (error.stderr or "").splitlines()
                      if line.startswith("X Error: ")]
            transient = ("X Error: 9: Bad Drawable", "X Error: 3: Bad Window")
            if error.returncode != 1 or not errors or any(
                    not line.startswith(transient) for line in errors):
                raise
        else:
            if name in windows:
                return
        time.sleep(1)
    raise RuntimeError(name + " window was not mapped in the Xfce display")


def verify_emutos_rom(rom, expected_sha256):
    """Bind the installed ROM bytes independently of their transport archive."""
    if not rom.is_file() or rom.stat().st_size != 256 * 1024:
        raise RuntimeError("pinned EmuTOS ROM missing or wrong size")
    rom_sha256 = hashlib.sha256(rom.read_bytes()).hexdigest()
    if rom_sha256 != expected_sha256:
        raise RuntimeError("pinned EmuTOS ROM digest mismatch")
    return rom_sha256


def diagnostics():
    """Observe startup even when no user session exists to run the witness."""
    source = json.loads(Path("/etc/qikvrt/distribution.json").read_text())["source_sha"]
    commands = {
        "display_manager": ["systemctl", "show", "lightdm.service", "-p", "ActiveState", "-p", "SubState", "-p", "Result"],
        "seat": ["loginctl", "show-seat", "seat0", "-p", "CanGraphical", "-p", "Sessions"],
        "live_user": ["getent", "passwd", "qikvrt"],
        "journal": ["journalctl", "-b", "-u", "lightdm.service", "--no-pager", "-n", "40"],
    }
    files = ("/var/log/lightdm/lightdm.log", "/var/log/lightdm/x-0.log", "/var/log/Xorg.0.log",
             "/home/qikvrt/.xsession-errors", "/home/qikvrt/.config/qikvrt/runtime-witness.log",
             "/home/qikvrt/.config/qikvrt/firefox.log", "/home/qikvrt/.config/qikvrt/hatari.log")
    for attempt in range(1, 5):
        time.sleep(45)
        observation = {"source_sha": source, "attempt": attempt, "effect_ack_done": False}
        for name, command in commands.items():
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=10)
                observation[name] = (result.stdout + result.stderr)[-4000:]
            except (OSError, subprocess.TimeoutExpired) as error:
                observation[name] = str(error)
        for name in files:
            path = Path(name)
            if path.is_file():
                observation[name] = path.read_text(errors="replace")[-6000:]
        message = "QIKVRT_GRAPHICS_DIAGNOSTICS " + json.dumps(observation, sort_keys=True) + "\n"
        try:
            with open("/dev/ttyS0", "w") as serial:
                serial.write(message)
        except OSError:
            print(message, flush=True)


def main():
    config = json.loads(Path("/etc/qikvrt/distribution.json").read_text())
    source = config["source_sha"]
    stage("source=" + source)
    spec = importlib.util.spec_from_file_location("qikvrt_boot", ROOT / "boot.py")
    boot = importlib.util.module_from_spec(spec); spec.loader.exec_module(boot)
    # The graphical session invokes this witness; an early systemd marker cannot satisfy it.
    run(["pgrep", "-u", str(os.getuid()), "xfce4-session"])
    stage("xfce-session-observed")
    wait_for_window("Firefox")
    run(["pgrep", "-u", str(os.getuid()), "firefox-esr"])
    stage("firefox-window-observed")
    with urllib.request.urlopen("http://127.0.0.1:8788/AI/", timeout=5) as response:
        ai_page = response.read()
    if b"epistemic spiral" not in ai_page.lower() or b"Universal Terminal" not in ai_page:
        raise RuntimeError("local /AI epistemic-spiral surface not observed")
    spiral_root = Path("/usr/share/qikvrt/web/assets/epistemic-spiral")
    manifest = json.loads((spiral_root / "manifest.json").read_text())
    i18n = json.loads((spiral_root / "i18n.json").read_text())
    bundle = {"schema":"qikvrt_epistemic_spiral_serialized_v1","manifest":manifest,
              "svg":(spiral_root / "spiral.svg").read_text(),"i18n":i18n}
    bundle_bytes = json.dumps(bundle,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    spiral_sha256 = hashlib.sha256(bundle_bytes).hexdigest()
    if spiral_sha256 != config["epistemic_spiral"]["carrier_sha256"]:
        raise RuntimeError("Linux spiral readback digest mismatch")
    firefox_package = Path(config["epistemic_spiral"]["firefox_extension_package"])
    if not firefox_package.is_file() or firefox_package.stat().st_size == 0:
        raise RuntimeError("Firefox Effect-Ack adapter package missing from distribution")
    stage("epistemic-spiral-ai-surface-readback")

    rom = Path("/usr/share/qikvrt/emutos/etos256de.img")
    rom_sha256 = verify_emutos_rom(rom, config["emutos_rom_sha256"])
    hatari_pid = run(["pgrep", "-u", str(os.getuid()), "-x", "hatari"]).splitlines()[0]
    cmdline = Path("/proc").joinpath(hatari_pid, "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
    if "--machine st" not in cmdline or str(rom) not in cmdline:
        raise RuntimeError("Hatari process is not bound to the pinned ST/EmuTOS subject")
    wait_for_window("Hatari")
    stage("hatari-emutos-window-observed")
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
               "hatari_process_observed": True, "hatari_machine": "st",
               "emutos_rom": str(rom), "emutos_rom_sha256": rom_sha256,
               "hatari_window_observed": True, "physical_atari_boot": False,
               "epistemic_spiral_carrier_sha256": spiral_sha256, "ai_surface_readback": True,
               "firefox_effect_ack_adapter_package_present": True,
               "firefox_effect_ack_adapter_signed": config["epistemic_spiral"]["firefox_extension_signed"],
               "effect_ack_done": False}
    Path.home().joinpath(".config/qikvrt/runtime-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    emit_serial("QIKVRT_RUNTIME_RECEIPT " + json.dumps(receipt, sort_keys=True))
    # The root-owned boot-scoped journal reader also covers user device denial.
    marker = "QIKVRT_MEGAST_RUNTIME_OK source_sha=" + source
    emit_serial(marker)
    subprocess.run(["logger", "-t", "qikvrt-runtime", marker], check=True)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--diagnostics"]:
            diagnostics()
        else:
            main()
    except Exception as error:
        traceback.print_exc()
        detail = str(error) + " " + str(getattr(error, "stderr", ""))
        marker = "QIKVRT_RUNTIME_BLOCK stage=" + LAST_STAGE + " error=" + detail[:2000]
        emit_serial(marker)
        subprocess.run(["logger", "-t", "qikvrt-runtime", marker], check=False)
        raise SystemExit(1)
