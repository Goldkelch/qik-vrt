#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
WORK=${QIKVRT_MEGAST_WORK:-"$ROOT/.build/qikvrt-megast"}
OUT=${QIKVRT_MEGAST_OUT:-"$ROOT/out"}
SHA=${QIKVRT_EXACT_SHA:-$(git -C "$ROOT" rev-parse HEAD)}

rm -rf "$WORK"
mkdir -p "$WORK/config/package-lists" \
         "$WORK/config/includes.chroot/usr/local/bin" \
         "$WORK/config/includes.chroot/etc/qikvrt" \
         "$WORK/config/includes.chroot/etc/xdg/autostart" \
         "$OUT"

cat > "$WORK/config/package-lists/qikvrt-megast.list.chroot" <<'EOF'
linux-image-amd64 live-boot systemd-sysv sudo ca-certificates curl git jq
xorg lightdm xfce4 xfce4-terminal dbus-x11
hatari firefox-esr flatpak podman xterm
python3 python3-venv nginx openssh-client
fonts-dejavu-core
EOF

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
lb config \
  --mode debian \
  --distribution trixie \
  --architectures amd64 \
  --binary-images iso-hybrid \
  --archive-areas "main contrib non-free-firmware" \
  --security true \
  --security-suite trixie-security \
  --updates true \
  --bootappend-live "boot=live components username=qikvrt hostname=qikvrt-megast"

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
  "next_required_effect": "boot_and_runtime_reobservation_then_public_download_readback"
}
EOF

echo "QIKVRT_MEGAST_BUILD_OK sha=$SHA iso_sha256=$ISO_SHA bytes=$ISO_BYTES"
