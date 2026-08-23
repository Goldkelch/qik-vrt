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
FILE="ubuntu-$REL-server-cloudimg-amd64.img"
BASE=""
for candidate in "https://cloud-images.ubuntu.com/releases/$REL/$BUILD" "https://cloud-images.ubuntu.com/releases/releases/noble/$BUILD"; do
  if curl -fsSLo SHA256SUMS "$candidate/SHA256SUMS"; then BASE="$candidate"; break; fi
done
[[ -n "$BASE" ]] || { echo "BLOCK: pinned Ubuntu cloud-image release unavailable" >&2; exit 2; }
curl -fsSLo SHA256SUMS.gpg "$BASE/SHA256SUMS.gpg"
curl -fsSLo "$FILE" "$BASE/$FILE"
gpgv --keyring /usr/share/keyrings/ubuntu-cloudimage-keyring.gpg SHA256SUMS.gpg SHA256SUMS
awk -v p="$FILE" '$2==p || $2=="*"p {print $1"  "p}' SHA256SUMS | sha256sum -c -
cp "$FILE" appliance.qcow2
qemu-img resize appliance.qcow2 16G
printf 'APT::Snapshot "%s";\n' "$SNAP" > 50qikvrt-snapshot
printf 'QIKVRT_IMAGE_REF=%s\nQIKVRT_VNC_PASSWORD=qikvrt\n' "$QIKVRT_IMAGE_REF" > qikvrt-mesh-appliance.env
cp "$ROOT/distribution/qikvrt-mesh-appliance/systemd/qikvrt-mesh-appliance.service" .
cp "$QIKVRT_OCI_ARCHIVE" appliance.oci.tar
virt-customize -a appliance.qcow2 --network \
  --copy-in 50qikvrt-snapshot:/etc/apt/apt.conf.d \
  --run-command "apt-get update --snapshot $SNAP" \
  --run-command "DEBIAN_FRONTEND=noninteractive apt-get install --snapshot $SNAP --no-install-recommends -y podman ca-certificates curl" \
  --mkdir /opt/qikvrt \
  --copy-in appliance.oci.tar:/opt/qikvrt \
  --copy-in qikvrt-mesh-appliance.env:/etc \
  --copy-in qikvrt-mesh-appliance.service:/etc/systemd/system \
  --run-command "podman load -i /opt/qikvrt/appliance.oci.tar" \
  --run-command "systemctl enable qikvrt-mesh-appliance.service" \
  --write "/etc/qikvrt-source-sha:$QIKVRT_SOURCE_SHA" \
  --run-command "apt-get clean && rm -rf /var/lib/apt/lists/*"
qemu-img convert -O vmdk -o subformat=streamOptimized appliance.qcow2 appliance.vmdk
qemu-img convert -O vhdx -o subformat=dynamic appliance.qcow2 appliance.vhdx
cat > appliance.ovf <<'OVF'
<?xml version="1.0" encoding="UTF-8"?>
<Envelope xmlns="http://schemas.dmtf.org/ovf/envelope/1" xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData" xmlns:vssd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData"><References><File ovf:id="disk1" ovf:href="qikvrt-mesh-appliance-amd64.vmdk"/></References><DiskSection><Info>Virtual disks</Info><Disk ovf:diskId="disk1" ovf:fileRef="disk1" ovf:capacity="17179869184" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized"/></DiskSection><NetworkSection><Info>Networks</Info><Network ovf:name="NAT"><Description>NAT</Description></Network></NetworkSection><VirtualSystem ovf:id="qikvrt"><Info>QIK-VRT Mesh Appliance</Info><Name>QIK-VRT Mesh Appliance</Name><OperatingSystemSection ovf:id="94"><Info>Ubuntu Linux 64-bit</Info></OperatingSystemSection><VirtualHardwareSection><Info>Hardware</Info><System><vssd:ElementName>Virtual Hardware Family</vssd:ElementName><vssd:InstanceID>0</vssd:InstanceID><vssd:VirtualSystemIdentifier>qikvrt</vssd:VirtualSystemIdentifier><vssd:VirtualSystemType>vmx-19</vssd:VirtualSystemType></System><Item><rasd:ElementName>2 CPUs</rasd:ElementName><rasd:InstanceID>1</rasd:InstanceID><rasd:ResourceType>3</rasd:ResourceType><rasd:VirtualQuantity>2</rasd:VirtualQuantity></Item><Item><rasd:ElementName>4096 MB RAM</rasd:ElementName><rasd:InstanceID>2</rasd:InstanceID><rasd:ResourceType>4</rasd:ResourceType><rasd:VirtualQuantity>4096</rasd:VirtualQuantity></Item><Item><rasd:ElementName>Disk</rasd:ElementName><rasd:HostResource>ovf:/disk/disk1</rasd:HostResource><rasd:InstanceID>3</rasd:InstanceID><rasd:ResourceType>17</rasd:ResourceType></Item><Item><rasd:AutomaticAllocation>true</rasd:AutomaticAllocation><rasd:Connection>NAT</rasd:Connection><rasd:ElementName>Network</rasd:ElementName><rasd:InstanceID>4</rasd:InstanceID><rasd:ResourceType>10</rasd:ResourceType></Item></VirtualHardwareSection></VirtualSystem></Envelope>
OVF
mv appliance.vmdk qikvrt-mesh-appliance-amd64.vmdk
tar --sort=name --mtime='UTC 1980-01-01' --owner=0 --group=0 --numeric-owner -cf "$OUT/qikvrt-mesh-appliance-amd64.ova" appliance.ovf qikvrt-mesh-appliance-amd64.vmdk
xz -T0 -9e -c appliance.qcow2 > "$OUT/qikvrt-mesh-appliance-amd64.qcow2.xz"
xz -T0 -9e -c qikvrt-mesh-appliance-amd64.vmdk > "$OUT/qikvrt-mesh-appliance-amd64.vmdk.xz"
xz -T0 -9e -c appliance.vhdx > "$OUT/qikvrt-mesh-appliance-amd64.vhdx.xz"
cp appliance.ovf "$OUT/qikvrt-mesh-appliance-amd64.ovf"
(cd "$OUT" && sha256sum qikvrt-mesh-appliance-amd64.* > SHA256SUMS-VM.txt)
