#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
CONTRACT="$ROOT/distribution/qikvrt-reference-minimal/BUILD_CONTRACT.json"
WORK=${QIKVRT_REFERENCE_WORK:-"$ROOT/.build/qikvrt-reference-minimal"}
OUT=${QIKVRT_REFERENCE_OUT:-"$ROOT/out/reference-minimal"}
SHA=${QIKVRT_EXACT_SHA:-$(git -C "$ROOT" rev-parse HEAD)}

[ "$SHA" = "$(git -C "$ROOT" rev-parse HEAD)" ] || {
  echo 'BLOCKED: exact source HEAD mismatch' >&2
  exit 70
}
TREE=$(git -C "$ROOT" rev-parse 'HEAD^{tree}')
SOURCE_DATE_EPOCH=$(git -C "$ROOT" show -s --format=%ct "$SHA")
case "$SOURCE_DATE_EPOCH" in
  ''|*[!0-9]*) echo 'BLOCKED: invalid source commit timestamp' >&2; exit 70 ;;
esac
export SOURCE_DATE_EPOCH
export TZ=UTC
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

CONTRACT_SHA=$(sha256sum "$CONTRACT" | awk '{print $1}')
SNAPSHOT=$(python3 - "$CONTRACT" <<'PY'
import json,sys
print(json.load(open(sys.argv[1], encoding='utf-8'))['distribution']['snapshot'])
PY
)
SUITE=$(python3 - "$CONTRACT" <<'PY'
import json,sys
print(json.load(open(sys.argv[1], encoding='utf-8'))['distribution']['suite'])
PY
)

rm -rf "$WORK"
mkdir -p "$WORK/config/package-lists" \
         "$WORK/config/includes.chroot/etc/qikvrt" \
         "$WORK/config/includes.chroot/usr/local/sbin" \
         "$WORK/config/includes.chroot/etc/systemd/system/multi-user.target.wants" \
         "$OUT"

python3 - "$CONTRACT" > "$WORK/config/package-lists/qikvrt-reference.list.chroot" <<'PY'
import json,sys
contract=json.load(open(sys.argv[1], encoding='utf-8'))
print(' '.join(contract['distribution']['packages']))
PY
cp "$CONTRACT" "$WORK/config/includes.chroot/etc/qikvrt/BUILD_CONTRACT.json"
cat > "$WORK/config/includes.chroot/etc/qikvrt/reference-subject.json" <<EOF2
{"schema":"qikvrt.reference-linux-subject.v1","source_sha":"$SHA","source_tree":"$TREE","source_date_epoch":$SOURCE_DATE_EPOCH,"contract_sha256":"$CONTRACT_SHA"}
EOF2

cat > "$WORK/config/includes.chroot/usr/local/sbin/qikvrt-reference-boot-witness" <<EOF2
#!/bin/sh
set -eu
printf '%s\n' 'QIKVRT_REFERENCE_LINUX_BOOT_OK source_sha=$SHA source_tree=$TREE contract_sha256=$CONTRACT_SHA'
EOF2
chmod 0755 "$WORK/config/includes.chroot/usr/local/sbin/qikvrt-reference-boot-witness"
cat > "$WORK/config/includes.chroot/etc/systemd/system/qikvrt-reference-boot-witness.service" <<'EOF2'
[Unit]
Description=QIK-VRT minimal reference Linux exact-subject boot witness
After=local-fs.target
Before=multi-user.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/qikvrt-reference-boot-witness
StandardOutput=tty
StandardError=tty
TTYPath=/dev/ttyS0
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF2
ln -s ../qikvrt-reference-boot-witness.service \
  "$WORK/config/includes.chroot/etc/systemd/system/multi-user.target.wants/qikvrt-reference-boot-witness.service"

cd "$WORK"
lb config \
  --mode debian \
  --distribution "$SUITE" \
  --architectures amd64 \
  --binary-images iso-hybrid \
  --archive-areas main \
  --mirror-bootstrap "$SNAPSHOT" \
  --mirror-chroot "$SNAPSHOT" \
  --mirror-binary "$SNAPSHOT" \
  --apt-options "--yes -oAcquire::Check-Valid-Until=false" \
  --apt-recommends false \
  --apt-source-archives false \
  --security false \
  --updates false \
  --utc-time true \
  --iso-application "QIK-VRT Reference Linux" \
  --iso-publisher "QIK-VRT" \
  --iso-volume "QIKVRT_REF_V1" \
  --bootappend-live "boot=live components console=tty0 console=ttyS0,115200n8"

lb build
ISO=$(find . -maxdepth 1 -type f \( -name 'live-image-*.hybrid.iso' -o -name 'live-image-amd64.hybrid.iso' \) | LC_ALL=C sort | head -n1)
[ -n "$ISO" ] || { echo 'BLOCKED: live-build produced no ISO' >&2; exit 70; }

ARTIFACT="$OUT/qikvrt-reference-linux-amd64.iso"
cp "$ISO" "$ARTIFACT"
ISO_SHA=$(sha256sum "$ARTIFACT" | awk '{print $1}')
ISO_BYTES=$(wc -c < "$ARTIFACT" | tr -d ' ')
printf '%s  %s\n' "$ISO_SHA" "$(basename "$ARTIFACT")" > "$ARTIFACT.sha256"

LB_VERSION=$(lb --version 2>&1 | head -n1 | sed 's/"/\\"/g')
XORRISO_VERSION=$(xorriso -version 2>&1 | head -n1 | sed 's/"/\\"/g')
SQUASHFS_VERSION=$(mksquashfs -version 2>&1 | head -n1 | sed 's/"/\\"/g')
DEBOOTSTRAP_VERSION=$(debootstrap --version 2>&1 | head -n1 | sed 's/"/\\"/g')
cat > "$OUT/qikvrt-reference-linux-build-receipt.json" <<EOF2
{
  "schema": "qikvrt.reference-linux-build-receipt.v1",
  "source_sha": "$SHA",
  "source_tree": "$TREE",
  "source_date_epoch": $SOURCE_DATE_EPOCH,
  "contract_sha256": "$CONTRACT_SHA",
  "snapshot": "$SNAPSHOT",
  "artifact": "qikvrt-reference-linux-amd64.iso",
  "sha256": "$ISO_SHA",
  "bytes": $ISO_BYTES,
  "toolchain": {
    "live_build": "$LB_VERSION",
    "xorriso": "$XORRISO_VERSION",
    "mksquashfs": "$SQUASHFS_VERSION",
    "debootstrap": "$DEBOOTSTRAP_VERSION"
  },
  "boot_witness_observed": false,
  "rebuild_sha256_match": false,
  "effect_ack_done": false
}
EOF2
printf 'QIKVRT_REFERENCE_BUILD_OK source_sha=%s iso_sha256=%s bytes=%s\n' "$SHA" "$ISO_SHA" "$ISO_BYTES"
