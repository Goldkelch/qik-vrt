#!/bin/bash
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
set -euo pipefail
IMAGE=${1:?container image required}
VERSION=${2:?version required}
OUT=${3:?output directory required}
SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-0}
DISK_GIB=${QIKVRT_VM_DISK_GIB:-8}
mkdir -p "$OUT"
OUT=$(realpath "$OUT")
work=$(mktemp -d)
loopdev=""
mountpoint="$work/root"
container=""
cleanup() {
  set +e
  mountpoint -q "$mountpoint/dev" && umount -R "$mountpoint/dev"
  mountpoint -q "$mountpoint/proc" && umount "$mountpoint/proc"
  mountpoint -q "$mountpoint/sys" && umount -R "$mountpoint/sys"
  mountpoint -q "$mountpoint" && umount "$mountpoint"
  [ -z "$loopdev" ] || losetup -d "$loopdev"
  [ -z "$container" ] || docker rm -f "$container" >/dev/null 2>&1
  rm -rf "$work"
}
trap cleanup EXIT
container=$(docker create "$IMAGE" /bin/true)
docker export "$container" > "$work/rootfs.tar"
raw="$work/QIKVRT-Mesh-Appliance-v${VERSION}-amd64.raw"
truncate -s "${DISK_GIB}G" "$raw"
parted -s "$raw" mklabel msdos mkpart primary ext4 1MiB 100% set 1 boot on
loopdev=$(losetup --find --show --partscan "$raw")
part="${loopdev}p1"
for _ in $(seq 1 20); do [ -b "$part" ] && break; sleep 0.2; done
[ -b "$part" ] || { echo "partition device unavailable" >&2; exit 2; }
mkfs.ext4 -F -L QIKVRT_MESH "$part"
mkdir -p "$mountpoint"
mount "$part" "$mountpoint"
tar --numeric-owner -xf "$work/rootfs.tar" -C "$mountpoint"
rm -f "$mountpoint/.dockerenv"
uuid=$(blkid -s UUID -o value "$part")
printf 'UUID=%s / ext4 defaults 0 1\n' "$uuid" > "$mountpoint/etc/fstab"
printf 'qikvrt-mesh\n' > "$mountpoint/etc/hostname"
mkdir -p "$mountpoint/etc/systemd/system/getty@tty1.service.d"
cat > "$mountpoint/etc/systemd/system/getty@tty1.service.d/autologin.conf" <<'EOF'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin qikvrt --noclear %I $TERM
EOF
mount --rbind /dev "$mountpoint/dev"
mount -t proc proc "$mountpoint/proc"
mount --rbind /sys "$mountpoint/sys"
chroot "$mountpoint" update-initramfs -u -k all
chroot "$mountpoint" grub-install --recheck --target=i386-pc --boot-directory=/boot "$loopdev"
chroot "$mountpoint" update-grub
sync
umount -R "$mountpoint/dev"
umount "$mountpoint/proc"
umount -R "$mountpoint/sys"
umount "$mountpoint"
losetup -d "$loopdev"
loopdev=""
base="QIKVRT-Mesh-Appliance-v${VERSION}-amd64"
qemu-img convert -p -c -O qcow2 -o compat=1.1,lazy_refcounts=on "$raw" "$OUT/$base.qcow2"
qemu-img convert -p -O vhdx -o subformat=dynamic "$raw" "$OUT/$base.vhdx"
qemu-img convert -p -O vmdk -o subformat=streamOptimized "$raw" "$OUT/$base.vmdk"
size=$(stat -c %s "$OUT/$base.vmdk")
capacity=$((DISK_GIB * 1024 * 1024 * 1024))
cat > "$work/$base.ovf" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<Envelope xmlns="http://schemas.dmtf.org/ovf/envelope/1" xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData" xmlns:vssd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData">
  <References><File ovf:id="file1" ovf:href="$base.vmdk" ovf:size="$size"/></References>
  <DiskSection><Info>Virtual disk</Info><Disk ovf:diskId="disk1" ovf:fileRef="file1" ovf:capacity="$capacity" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized"/></DiskSection>
  <NetworkSection><Info>Logical network</Info><Network ovf:name="NAT"><Description>NAT network</Description></Network></NetworkSection>
  <VirtualSystem ovf:id="qikvrt-mesh"><Info>QIK-VRT Mesh Appliance</Info><Name>QIK-VRT Mesh Appliance v$VERSION</Name><OperatingSystemSection ovf:id="96"><Info>Debian GNU/Linux 12</Info><Description>Debian_64</Description></OperatingSystemSection><VirtualHardwareSection><Info>Virtual hardware</Info><System><vssd:ElementName>Virtual Hardware Family</vssd:ElementName><vssd:InstanceID>0</vssd:InstanceID><vssd:VirtualSystemIdentifier>qikvrt-mesh</vssd:VirtualSystemIdentifier><vssd:VirtualSystemType>vmx-19</vssd:VirtualSystemType></System><Item><rasd:Caption>2 virtual CPU</rasd:Caption><rasd:ElementName>2 virtual CPU</rasd:ElementName><rasd:InstanceID>1</rasd:InstanceID><rasd:ResourceType>3</rasd:ResourceType><rasd:VirtualQuantity>2</rasd:VirtualQuantity></Item><Item><rasd:Caption>4096 MB RAM</rasd:Caption><rasd:ElementName>4096 MB RAM</rasd:ElementName><rasd:InstanceID>2</rasd:InstanceID><rasd:ResourceType>4</rasd:ResourceType><rasd:VirtualQuantity>4096</rasd:VirtualQuantity><rasd:AllocationUnits>byte * 2^20</rasd:AllocationUnits></Item><Item><rasd:Caption>disk1</rasd:Caption><rasd:InstanceID>3</rasd:InstanceID><rasd:HostResource>ovf:/disk/disk1</rasd:HostResource><rasd:ResourceType>17</rasd:ResourceType></Item><Item><rasd:Caption>NAT adapter</rasd:Caption><rasd:InstanceID>4</rasd:InstanceID><rasd:ResourceType>10</rasd:ResourceType><rasd:Connection>NAT</rasd:Connection></Item></VirtualHardwareSection></VirtualSystem>
</Envelope>
EOF
cp "$OUT/$base.vmdk" "$work/$base.vmdk"
(
  cd "$work"
  sha256sum "$base.ovf" "$base.vmdk" > "$base.mf"
  tar --sort=name --mtime="@$SOURCE_DATE_EPOCH" --owner=0 --group=0 --numeric-owner -cf "$OUT/$base.ova" "$base.ovf" "$base.mf" "$base.vmdk"
)
rm -f "$OUT/$base.vmdk"
sha256sum "$OUT/$base.qcow2" "$OUT/$base.vhdx" "$OUT/$base.ova" > "$OUT/$base-SHA256SUMS.txt"
