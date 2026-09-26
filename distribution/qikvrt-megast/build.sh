#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
WORK=${QIKVRT_MEGAST_WORK:-"$ROOT/.build/qikvrt-megast"}
OUT=${QIKVRT_MEGAST_OUT:-"$ROOT/out"}
SHA=${QIKVRT_EXACT_SHA:-$(git -C "$ROOT" rev-parse HEAD)}

rm -rf "$WORK"
mkdir -p "$WORK/config/package-lists" \
         "$WORK/config/archives" \
         "$WORK/config/includes.chroot/usr/local/bin" \
         "$WORK/config/includes.chroot/usr/share/qikvrt/emutos" \
         "$WORK/config/includes.chroot/usr/share/hatari" \
         "$WORK/config/includes.chroot/etc/qikvrt" \
         "$WORK/config/includes.chroot/etc/xdg/autostart" \
         "$WORK/config/includes.chroot/etc/systemd/system/multi-user.target.wants" \
         "$WORK/config/includes.chroot/etc/systemd/system" \
         "$OUT"

cat > "$WORK/config/package-lists/qikvrt-megast.list.chroot" <<'EOF'
linux-image-amd64 live-boot systemd-sysv sudo ca-certificates curl git jq
xorg lightdm xfce4 xfce4-terminal dbus-x11
hatari firefox-esr flatpak podman xterm
python3 python3-venv nginx openssh-client openssh-server kmod
fonts-dejavu-core qemu-user x11-utils procps
EOF

# Materialize a legally redistributable, exact-byte EmuTOS ROM for Hatari.
# The real end-user VirtualBox witness reached Hatari but failed because
# /usr/share/hatari/tos.img was absent. Keep proprietary Atari TOS excluded.
EMUTOS_LOCK="$ROOT/runtime/toolchains/emutos-1.4.lock.json"
EMUTOS_URL=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["source"])' "$EMUTOS_LOCK")
EMUTOS_SHA=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["sha256"])' "$EMUTOS_LOCK")
EMUTOS_ROM=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["rom"])' "$EMUTOS_LOCK")
EMUTOS_ROM_SHA=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["rom_sha256"])' "$EMUTOS_LOCK")
EMUTOS_ARCHIVE="$WORK/emutos.zip"
curl -fL --proto '=https' --proto-redir '=https' --max-redirs 5 --connect-timeout 20 --max-time 180 \
  -o "$EMUTOS_ARCHIVE" "$EMUTOS_URL"
printf '%s  %s\n' "$EMUTOS_SHA" "$EMUTOS_ARCHIVE" | sha256sum -c -
python3 - "$EMUTOS_ARCHIVE" "$EMUTOS_ROM" "$WORK/config/includes.chroot/usr/share/qikvrt/emutos" "$EMUTOS_ROM_SHA" <<'PY'
import hashlib,pathlib,sys,zipfile
archive=pathlib.Path(sys.argv[1]); wanted=sys.argv[2]; out=pathlib.Path(sys.argv[3])
with zipfile.ZipFile(archive) as z:
    matches=[n for n in z.namelist() if pathlib.PurePosixPath(n).name == wanted]
    if len(matches) != 1:
        raise SystemExit("BLOCKED: exact EmuTOS ROM not uniquely present")
    data=z.read(matches[0])
    if len(data) != 256 * 1024:
        raise SystemExit("BLOCKED: EmuTOS ROM size mismatch")
    if hashlib.sha256(data).hexdigest() != sys.argv[4]:
        raise SystemExit("BLOCKED: EmuTOS ROM digest mismatch")
    (out / wanted).write_bytes(data)
PY
ln -s "../qikvrt/emutos/$EMUTOS_ROM" "$WORK/config/includes.chroot/usr/share/hatari/tos.img"
test -s "$WORK/config/includes.chroot/usr/share/qikvrt/emutos/$EMUTOS_ROM"
test -L "$WORK/config/includes.chroot/usr/share/hatari/tos.img"

# Compile the real C90 corpus and the CPU-family bootstrap program into the guest.
TREE=$(git -C "$ROOT" rev-parse 'HEAD^{tree}')
[ "$SHA" = "$(git -C "$ROOT" rev-parse HEAD)" ] || { echo 'BLOCKED: source HEAD mismatch' >&2; exit 70; }
GUEST="$WORK/config/includes.chroot"
mkdir -p "$GUEST/opt/qikvrt/runtime" "$GUEST/opt/qikvrt/smalltalk" \
         "$GUEST/etc/lightdm/lightdm.conf.d" \
         "$GUEST/etc/systemd/system/lightdm.service.d"
cc -std=c90 -pedantic -Wall -Wextra -Werror -O2 -I"$ROOT/include" \
  "$ROOT/src/effect_ack_core.c" "$ROOT/tests/test_effect_ack_core.c" \
  -o "$GUEST/usr/local/bin/qikvrt-c90-selftest"
cc -std=c90 -pedantic -Wall -Wextra -Werror -O2 -I"$ROOT/src/cloud_transputer" \
  "$ROOT/src/cloud_transputer/qikvrt_boot_receive.c" \
  "$ROOT/src/cloud_transputer/qikvrt_wire_v1.c" "$ROOT/src/cloud_transputer/qikvrt_sha256_v1.c" \
  -o "$GUEST/usr/local/bin/qikvrt-boot-receive"
m68k-linux-gnu-gcc -m68000 -static -std=c90 -pedantic -Wall -Wextra -Werror -O2 \
  "$ROOT/src/cloud_transputer/m68k_contract_probe.c" -o "$GUEST/opt/qikvrt/runtime/QIKVRT_BOOT.BIN"
cp "$GUEST/opt/qikvrt/runtime/QIKVRT_BOOT.BIN" "$OUT/QIKVRT_BOOT.BIN"
python3 -B "$ROOT/tools/qikvrt_smalltalk.py" install
python3 -B "$ROOT/tools/qikvrt_smalltalk.py" build --output "$GUEST/opt/qikvrt/smalltalk"
# The lock owns the cache identity; an explicit dependency update must not
# silently copy the previous version into the fresh distribution.
PHARO_VERSION=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$ROOT/runtime/toolchains/pharo-13.lock.json")
cp -a "${QIKVRT_TOOLCHAIN_CACHE:-$ROOT/.qikvrt/toolchains}/pharo/$PHARO_VERSION/vm" "$GUEST/opt/qikvrt/pharo-vm"
cp "$ROOT/src/smalltalk/smoke.st" "$GUEST/opt/qikvrt/smalltalk/"
cp "$ROOT/runtime/toolchains/"pharo-*-LICENSE.txt "$GUEST/opt/qikvrt/smalltalk/"
cp "$ROOT/distribution/qikvrt-megast/boot.py" "$GUEST/opt/qikvrt/boot.py"
cp "$ROOT/next/tools/node.py" "$GUEST/opt/qikvrt/node.py"
cp "$ROOT/next/deploy/qikvrt-repository-node@.service" "$GUEST/etc/systemd/system/"
# Node certificates and profiles are provisioned per owner, never baked into an image.
# Reuse the universal C90/Rust runtime; the desktop is its local terminal.
# Cargo's lock and the existing isolated toolchain bootstrap own dependencies.
TRANSPUTER_TOOLS="${QIKVRT_TARGET_TOOLS:-$WORK/target-tools}"
python3 -B "$ROOT/next/tools/bootstrap.py" --prefix "$TRANSPUTER_TOOLS" --install
. "$TRANSPUTER_TOOLS/target-env.sh"
"$QIKVRT_CARGO" build --release --locked --manifest-path "$ROOT/next/Cargo.toml"
install -m 0755 "$ROOT/next/target/release/qikvrt-next" "$GUEST/usr/local/bin/qikvrt-next"
install -m 0644 "$ROOT/next/examples/boolean_roundtrip.temdd" "$GUEST/opt/qikvrt/boolean_roundtrip.temdd"
TRANSPUTER_SHA=$(sha256sum "$GUEST/usr/local/bin/qikvrt-next" | cut -d ' ' -f 1)
TRANSPUTER_PROGRAM_SHA=$(sha256sum "$GUEST/opt/qikvrt/boolean_roundtrip.temdd" | cut -d ' ' -f 1)
cat > "$GUEST/etc/systemd/system/qikvrt-transputer.service" <<'EOF'
[Unit]
Description=QIK-VRT Universal Transputer and TEMDD Terminal
Wants=live-config.service
After=live-config.service network.target
[Service]
User=qikvrt
Group=qikvrt
StateDirectory=qikvrt-transputer
StateDirectoryMode=0700
UMask=0077
ExecStart=/usr/bin/python3 -B /opt/qikvrt/boot.py transputer-guest
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
ln -s ../qikvrt-transputer.service "$GUEST/etc/systemd/system/multi-user.target.wants/qikvrt-transputer.service"
CODEX_LOCK="$ROOT/runtime/toolchains/codex-0.155.1.lock.json"
CODEX_VERSION=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$CODEX_LOCK")
python3 -B "$ROOT/distribution/qikvrt-megast/boot.py" codex-install \
  "$CODEX_LOCK" "$GUEST/opt/qikvrt/codex" \
  "${QIKVRT_TOOLCHAIN_CACHE:-$ROOT/.qikvrt/toolchains}/codex/$CODEX_VERSION"
ln -s /opt/qikvrt/codex/bin/codex "$GUEST/usr/local/bin/codex"
# Package-relative resource discovery preserves the upstream helper binaries.
test "$("$GUEST/opt/qikvrt/codex/bin/codex" --version)" = "codex-cli $CODEX_VERSION"
mkdir -p "$GUEST/usr/share/applications"
cat > "$GUEST/usr/share/applications/qikvrt-chatgpt-connect.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=ChatGPT verbinden
Comment=Anmelden und einen echten kurzlebigen Kopplungscode anzeigen
Exec=xfce4-terminal --hold --command="/usr/bin/python3 -B /opt/qikvrt/boot.py chatgpt-connect"
Icon=utilities-terminal
Terminal=false
Categories=Network;
EOF
# Reuse the Universal Terminal SSH policy. The live guest narrows it to qikvrt,
# with a fresh host key and an explicit owner public key supplied at VM startup.
mkdir -p "$GUEST/etc/ssh" "$WORK/config/hooks/live"
cp "$ROOT/deploy/universal-terminal/sshd_config" "$GUEST/etc/ssh/qikvrt_sshd_config"
for unit in ssh.service ssh.socket sshd.service; do
  ln -sf /dev/null "$GUEST/etc/systemd/system/$unit"
done
cat > "$WORK/config/hooks/live/0999-no-image-ssh-host-keys.hook.chroot" <<'EOF'
#!/bin/sh
set -eu
rm -f /etc/ssh/ssh_host_* /var/lib/qikvrt/ssh/ssh_host_*
EOF
chmod 0755 "$WORK/config/hooks/live/0999-no-image-ssh-host-keys.hook.chroot"
cat > "$GUEST/etc/systemd/system/qikvrt-ssh.service" <<'EOF'
[Unit]
Description=QIK-VRT opt-in Universal Terminal SSH
Wants=live-config.service
After=live-config.service network.target
[Service]
ExecStartPre=-/usr/sbin/modprobe qemu_fw_cfg
ExecStart=/usr/bin/python3 -B /opt/qikvrt/boot.py ssh-guest
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
ln -s ../qikvrt-ssh.service "$GUEST/etc/systemd/system/multi-user.target.wants/qikvrt-ssh.service"
cp "$ROOT/distribution/qikvrt-megast/runtime-witness.py" "$GUEST/opt/qikvrt/runtime-witness.py"
cp "$ROOT/src/qikvrt_effect_ack_http_terminal.py" "$GUEST/opt/qikvrt/effect-ack-http.py"
cat > "$GUEST/etc/systemd/system/qikvrt-effect-ack-http.service" <<'EOF'
[Unit]
Description=QIK-VRT loopback Effect-Ack terminal
After=network.target
[Service]
ExecStart=/usr/bin/python3 -B /opt/qikvrt/effect-ack-http.py --host 127.0.0.1 --port 8771
DynamicUser=yes
NoNewPrivileges=yes
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOF
ln -s ../qikvrt-effect-ack-http.service "$GUEST/etc/systemd/system/multi-user.target.wants/qikvrt-effect-ack-http.service"
# Follow only this boot's runtime witness. logger accepting a message proves
# journal transport, not console delivery. A separate root-owned reader writes
# the serial device without granting the desktop user additional device access
# or blocking journald on synchronous forwarding of all system messages.
cat > "$GUEST/etc/systemd/system/qikvrt-runtime-serial.service" <<'EOF'
[Unit]
Description=QIK-VRT runtime witness serial return channel
After=systemd-journald.service
Before=lightdm.service
[Service]
Type=simple
ExecStart=/usr/bin/journalctl --boot --follow --lines=all --no-pager --output=cat --identifier=qikvrt-runtime
StandardOutput=tty
StandardError=journal
TTYPath=/dev/ttyS0
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOF
ln -s ../qikvrt-runtime-serial.service "$GUEST/etc/systemd/system/multi-user.target.wants/qikvrt-runtime-serial.service"

# This appliance must start the actual Xfce session without a greeter action.
# A virtual display remains usable when logind has not marked its seat graphical.
cat > "$GUEST/etc/lightdm/lightdm.conf.d/90-qikvrt-live.conf" <<'EOF'
[LightDM]
logind-check-graphical=false
[Seat:*]
autologin-user=qikvrt
autologin-user-timeout=0
autologin-session=xfce
user-session=xfce
allow-guest=false
EOF
cat > "$GUEST/etc/systemd/system/lightdm.service.d/10-qikvrt-live.conf" <<'EOF'
[Unit]
Wants=live-config.service
After=live-config.service
EOF
cat > "$GUEST/etc/systemd/system/qikvrt-graphics-diagnostics.service" <<'EOF'
[Unit]
Description=Bounded QIK-VRT graphical startup diagnostics
After=live-config.service
[Service]
Type=simple
ExecStart=/usr/bin/python3 -B /opt/qikvrt/runtime-witness.py --diagnostics
[Install]
WantedBy=multi-user.target
EOF
ln -s ../qikvrt-graphics-diagnostics.service "$GUEST/etc/systemd/system/multi-user.target.wants/qikvrt-graphics-diagnostics.service"

install -m 0755 "$ROOT/distribution/qikvrt-megast/qikvrt-megast-session.sh" \
  "$WORK/config/includes.chroot/usr/local/bin/qikvrt-megast-session"

cat > "$WORK/config/includes.chroot/etc/xdg/autostart/qikvrt-megast.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=QIK-VRT Mega ST Session
Exec=/usr/local/bin/qikvrt-megast-session
OnlyShowIn=XFCE;
X-GNOME-Autostart-enabled=true
EOF

cat > "$WORK/config/includes.chroot/usr/local/bin/qikvrt-megast-boot-witness" <<EOF
#!/bin/sh
set -eu
receipt=/run/qikvrt-megast-boot-receipt.json
cat > "\$receipt" <<JSON
{"schema":"qikvrt_megast_boot_receipt_v1","source_sha":"$SHA","booted":true,"effect_ack_done":false}
JSON
printf 'QIKVRT_MEGAST_BOOT_OK source_sha=%s\n' '$SHA' >/dev/ttyS0 2>/dev/null || true
EOF
chmod 0755 "$WORK/config/includes.chroot/usr/local/bin/qikvrt-megast-boot-witness"

cat > "$WORK/config/includes.chroot/etc/systemd/system/qikvrt-megast-boot-witness.service" <<'EOF'
[Unit]
Description=QIK-VRT Mega ST exact-subject boot witness
After=local-fs.target
Before=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/qikvrt-megast-boot-witness
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
ln -s ../qikvrt-megast-boot-witness.service \
  "$WORK/config/includes.chroot/etc/systemd/system/multi-user.target.wants/qikvrt-megast-boot-witness.service"

cat > "$WORK/config/includes.chroot/etc/qikvrt/distribution.json" <<EOF
{
  "schema": "qikvrt_megast_distribution_v1",
  "source_sha": "$SHA",
  "source_tree": "$TREE",
  "universal_transputer": {"binary_sha256": "$TRANSPUTER_SHA", "program_sha256": "$TRANSPUTER_PROGRAM_SHA", "terminal": "http://127.0.0.1:8772/AI", "store": "/var/lib/qikvrt-transputer/store"},
  "codex": $(cat "$GUEST/opt/qikvrt/codex/qikvrt-install-receipt.json"),
  "ssh": {"activation": "explicit_owner_public_key", "user": "qikvrt", "port": 2222, "chatgpt_pairing": "NOT_ESTABLISHED"},
  "emutos_rom_sha256": "$EMUTOS_ROM_SHA",
  "temdd": ["REQUEST", "EXECUTE", "FOLLOW", "LEARN", "REPEAT_UNTIL_DONE"],
  "principle": "Stay fail closed and keep future open!",
  "effect_ack_done": false,
  "atari_rom_policy": "NO_PROPRIETARY_TOS_REDISTRIBUTION",
  "modern_software_envelope": ["debian", "flatpak", "oci-podman", "web"]
}
EOF

cd "$WORK"
set -- lb config \
  --mode debian \
  --distribution trixie \
  --architectures amd64 \
  --binary-images iso-hybrid \
  --archive-areas "main contrib non-free-firmware"
if lb config --help 2>&1 | grep -q -- '--security-suite'; then
  set -- "$@" --security true --security-suite trixie-security
else
  printf '%s\n' \
    'deb http://security.debian.org/debian-security trixie-security main contrib non-free-firmware' \
    > "$WORK/config/archives/qikvrt-security.list.chroot"
  set -- "$@" --security false
fi
if lb config --help 2>&1 | grep -q -- '--updates'; then
  set -- "$@" --updates true
fi
set -- "$@" \
  --bootappend-live "boot=live components username=qikvrt hostname=qikvrt-megast console=tty0 console=ttyS0,115200n8"
"$@"

lb build

ISO=$(find . -maxdepth 1 -type f \( -name 'live-image-*.hybrid.iso' -o -name 'live-image-amd64.hybrid.iso' \) | head -n1)
[ -n "$ISO" ] || { echo "BLOCKED: live-build produced no ISO" >&2; exit 70; }

cp "$ISO" "$OUT/qikvrt-megast-amd64.iso"
(
  cd "$OUT"
  sha256sum qikvrt-megast-amd64.iso > qikvrt-megast-amd64.iso.sha256
)
ISO_SHA=$(awk '{print $1}' "$OUT/qikvrt-megast-amd64.iso.sha256")
ISO_BYTES=$(wc -c < "$OUT/qikvrt-megast-amd64.iso" | tr -d ' ')
cat > "$OUT/qikvrt-megast-build-receipt.json" <<EOF
{
  "schema": "qikvrt_megast_build_receipt_v1",
  "source_sha": "$SHA",
  "source_tree": "$TREE",
  "artifact": "qikvrt-megast-amd64.iso",
  "sha256": "$ISO_SHA",
  "bytes": $ISO_BYTES,
  "transport_ack": true,
  "effect_ack_done": false,
  "next_required_effect": "mount_boot_runtime_reobservation_then_public_download_readback"
}
EOF

echo "QIKVRT_MEGAST_BUILD_OK sha=$SHA iso_sha256=$ISO_SHA bytes=$ISO_BYTES"
