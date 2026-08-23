#!/usr/bin/env bash
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
set -euo pipefail
: "${QIKVRT_OCI_ARCHIVE:?required}" "${QIKVRT_IMAGE_REF:?required}" "${QIKVRT_SOURCE_SHA:?required}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
OUT="${QIKVRT_VM_OUT:-$PWD/dist-vm}"
mkdir -p "$OUT/work"
cd "$OUT/work"
REL="${QIKVRT_UBUNTU_RELEASE:-24.04}"
BUILD="${QIKVRT_UBUNTU_IMAGE_BUILD:-release-20260814}"
SNAP="${QIKVRT_UBUNTU_SNAPSHOT:-20260823T000000Z}"
VERSION="${QIKVRT_APPLIANCE_VERSION:-0.1.0-rc1}"
FILE="ubuntu-$REL-server-cloudimg-amd64.img"
BASE=""
for candidate in \
  "https://cloud-images.ubuntu.com/releases/$REL/$BUILD" \
  "https://cloud-images.ubuntu.com/releases/releases/noble/$BUILD"; do
  if curl -fsSLo SHA256SUMS "$candidate/SHA256SUMS"; then BASE="$candidate"; break; fi
done
[[ -n "$BASE" ]] || { echo "BLOCK: pinned Ubuntu cloud-image release unavailable" >&2; exit 2; }
curl -fsSLo SHA256SUMS.gpg "$BASE/SHA256SUMS.gpg"
curl -fsSLo "$FILE" "$BASE/$FILE"
gpgv --keyring /usr/share/keyrings/ubuntu-cloudimage-keyring.gpg SHA256SUMS.gpg SHA256SUMS
expected="$(awk -v p="$FILE" '$2==p || $2=="*"p {print $1}' SHA256SUMS)"
[[ ${#expected} -eq 64 ]] || { echo "BLOCK: pinned cloud image missing from signed inventory" >&2; exit 2; }
echo "$expected  $FILE" | sha256sum -c -
cp "$FILE" appliance.qcow2
qemu-img resize appliance.qcow2 8G
printf 'APT::Snapshot "%s";\n' "$SNAP" > 50qikvrt-snapshot
printf 'QIKVRT_IMAGE_REF=%s\nQIKVRT_VNC_PASSWORD=qikvrt\n' "$QIKVRT_IMAGE_REF" > qikvrt-mesh-appliance.env
cp "$ROOT/distribution/qikvrt-mesh-appliance/systemd/qikvrt-mesh-appliance.service" .
cp "$QIKVRT_OCI_ARCHIVE" appliance.oci.tar
virt-customize -a appliance.qcow2 --network \
  --copy-in 50qikvrt-snapshot:/etc/apt/apt.conf.d \
  --run-command "apt-get update --snapshot $SNAP" \
  --run-command "DEBIAN_FRONTEND=noninteractive apt-get install --snapshot $SNAP --no-install-recommends -y podman ca-certificates curl" \
  --mkdir /opt/qikvrt \
  --mkdir /var/lib/qikvrt \
  --copy-in appliance.oci.tar:/opt/qikvrt \
  --copy-in qikvrt-mesh-appliance.env:/etc \
  --copy-in qikvrt-mesh-appliance.service:/etc/systemd/system \
  --run-command "systemctl enable qikvrt-mesh-appliance.service" \
  --write "/etc/qikvrt-source-sha:$QIKVRT_SOURCE_SHA" \
  --write "/etc/qikvrt-appliance-version:$VERSION" \
  --run-command "apt-get clean && rm -rf /var/lib/apt/lists/*"
qemu-img convert -O vmdk -o subformat=streamOptimized appliance.qcow2 appliance.vmdk
qemu-img convert -O vhdx -o subformat=dynamic appliance.qcow2 appliance.vhdx
cat > appliance.ovf <<'OVF'
<?xml version="1.0" encoding="UTF-8"?>
<Envelope xmlns="http://schemas.dmtf.org/ovf/envelope/1" xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData" xmlns:vssd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData"><References><File ovf:id="disk1" ovf:href="qikvrt-mesh-appliance-amd64.vmdk"/></References><DiskSection><Info>Virtual disks</Info><Disk ovf:diskId="disk1" ovf:fileRef="disk1" ovf:capacity="8589934592" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized"/></DiskSection><NetworkSection><Info>Networks</Info><Network ovf:name="NAT"><Description>NAT</Description></Network></NetworkSection><VirtualSystem ovf:id="qikvrt"><Info>QIK-VRT Mesh Appliance</Info><Name>QIK-VRT Mesh Appliance</Name><OperatingSystemSection ovf:id="94"><Info>Ubuntu Linux 64-bit</Info></OperatingSystemSection><VirtualHardwareSection><Info>Hardware</Info><System><vssd:ElementName>Virtual Hardware Family</vssd:ElementName><vssd:InstanceID>0</vssd:InstanceID><vssd:VirtualSystemIdentifier>qikvrt</vssd:VirtualSystemIdentifier><vssd:VirtualSystemType>vmx-19</vssd:VirtualSystemType></System><Item><rasd:ElementName>2 CPUs</rasd:ElementName><rasd:InstanceID>1</rasd:InstanceID><rasd:ResourceType>3</rasd:ResourceType><rasd:VirtualQuantity>2</rasd:VirtualQuantity></Item><Item><rasd:ElementName>4096 MB RAM</rasd:ElementName><rasd:InstanceID>2</rasd:InstanceID><rasd:ResourceType>4</rasd:ResourceType><rasd:VirtualQuantity>4096</rasd:VirtualQuantity></Item><Item><rasd:ElementName>Disk</rasd:ElementName><rasd:HostResource>ovf:/disk/disk1</rasd:HostResource><rasd:InstanceID>3</rasd:InstanceID><rasd:ResourceType>17</rasd:ResourceType></Item><Item><rasd:AutomaticAllocation>true</rasd:AutomaticAllocation><rasd:Connection>NAT</rasd:Connection><rasd:ElementName>Network</rasd:ElementName><rasd:InstanceID>4</rasd:InstanceID><rasd:ResourceType>10</rasd:ResourceType></Item></VirtualHardwareSection></VirtualSystem></Envelope>
OVF
mv appliance.vmdk qikvrt-mesh-appliance-amd64.vmdk
prefix="QIKVRT-Mesh-Appliance-v$VERSION-amd64"
tar --sort=name --mtime='UTC 1980-01-01' --owner=0 --group=0 --numeric-owner -cf "$OUT/$prefix.ova" appliance.ovf qikvrt-mesh-appliance-amd64.vmdk
xz -T0 -6 -c appliance.qcow2 > "$OUT/$prefix.qcow2.xz"
xz -T0 -6 -c qikvrt-mesh-appliance-amd64.vmdk > "$OUT/$prefix.vmdk.xz"
xz -T0 -6 -c appliance.vhdx > "$OUT/$prefix.vhdx.xz"
cp appliance.ovf "$OUT/$prefix.ovf"
(cd "$OUT" && sha256sum "$prefix".* | LC_ALL=C sort > "QIKVRT-Mesh-Appliance-v$VERSION-VM-SHA256SUMS.txt")
