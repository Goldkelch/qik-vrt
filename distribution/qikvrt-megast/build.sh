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
         "$WORK/config/includes.chroot/etc/qikvrt" \
         "$WORK/config/includes.chroot/etc/xdg/autostart" \
         "$WORK/config/includes.chroot/etc/systemd/system/multi-user.target.wants" \
         "$WORK/config/includes.chroot/etc/systemd/system" \
         "$OUT"

cat > "$WORK/config/package-lists/qikvrt-megast.list.chroot" <<'EOF'
linux-image-amd64 live-boot systemd-sysv sudo ca-certificates curl git jq
xorg lightdm xfce4 xfce4-terminal dbus-x11
hatari firefox-esr flatpak podman xterm
python3 python3-venv nginx openssh-client
fonts-dejavu-core rsyslog qemu-user x11-utils procps
EOF

# Compile the real C90 corpus and the CPU-family bootstrap program into the guest.
GUEST="$WORK/config/includes.chroot"
mkdir -p "$GUEST/opt/qikvrt/runtime" "$GUEST/opt/qikvrt/smalltalk" \
         "$GUEST/etc/rsyslog.d" "$GUEST/etc/lightdm/lightdm.conf.d" \
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
cp -a "${QIKVRT_TOOLCHAIN_CACHE:-$ROOT/.qikvrt/toolchains}/pharo/13.1-4f7563dfe5-vm33501fd6/vm" "$GUEST/opt/qikvrt/pharo-vm"
cp "$ROOT/src/smalltalk/smoke.st" "$GUEST/opt/qikvrt/smalltalk/"
cp "$ROOT/runtime/toolchains/"pharo-*-LICENSE.txt "$GUEST/opt/qikvrt/smalltalk/"
cp "$ROOT/distribution/qikvrt-megast/boot.py" "$GUEST/opt/qikvrt/boot.py"
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
cat > "$GUEST/etc/rsyslog.d/30-qikvrt-runtime.conf" <<'EOF'
if $programname == 'qikvrt-runtime' then /dev/ttyS0
EOF

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
  "artifact": "qikvrt-megast-amd64.iso",
  "sha256": "$ISO_SHA",
  "bytes": $ISO_BYTES,
  "transport_ack": true,
  "effect_ack_done": false,
  "next_required_effect": "mount_boot_runtime_reobservation_then_public_download_readback"
}
EOF

echo "QIKVRT_MEGAST_BUILD_OK sha=$SHA iso_sha256=$ISO_SHA bytes=$ISO_BYTES"
