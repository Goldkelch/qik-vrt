#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Build exact QIK-VRT Mesh Linux OCI and VM assets."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, time
from pathlib import Path
from typing import Any

VERSION="1.0.0"
AUTHORITY_BASE="3cb6273924f3de310e3bd1cd5b827e8e3529220a"
FIREFOX_EFFECT_SHA="b7c9fa5f74cb963ba7cfefed2a0d0a071e6515a9"
ATARI_BROWSER_SHA="cba166e45a0ea4b5d5dd2ef9cde0ad96ff57554b"
AUTONOMOUS_REPAIR_SHA="9832f6ddf6a3ef53a7c0f9b52d2c9d8f1e7ba970"
FIREFOX_VERSION="153.0.4"
GECKO_VERSION="0.37.1"
UBUNTU_RELEASE="20260801"
UBUNTU_RELEASE_MIN_EPOCH=1785542400
MAX_SUPPORTED_BUILD_EPOCH=4102444800
CLOCK_CUSHION_SECONDS=300
CLOCK_OBSERVATION_WINDOW_SECONDS=30
TRUSTED_HOST_EPOCH_BACKWARD_SKEW_SECONDS=30
TRUSTED_HOST_EPOCH_MAX_AGE_SECONDS=7200
APT_SOURCE_DATE_OVERRIDE_REGEX=r'(^[[:space:]]*(Check-Date|Check-Valid-Until)[[:space:]]*:)|(^[[:space:]]*deb(-src)?[[:space:]]+\[[^]]*(check-date|check-valid-until)[[:space:]]*=)'
VM_DISK_SIZE_BYTES=20*1024**3
VM_ROOT_FILESYSTEM_MIN_BYTES=18*1024**3
UBUNTU_CLOUD_ROOT_PARTITION="/dev/sda1"
VM_PAYLOAD_RECEIPT_PATH="/etc/qikvrt/BUILD_ACCEPTANCE"
VM_PAYLOAD_RECEIPT="QIKVRT_VM_PAYLOAD_READBACK=OK"
UBUNTU_BASE=f"https://cloud-images.ubuntu.com/releases/noble/release-{UBUNTU_RELEASE}"
ARCH={
 "amd64":{
  "rootfs":"ubuntu-24.04-server-cloudimg-amd64-root.tar.xz",
  "rootfs_sha":"d93271f4e4f4bb0eafe73796c415dab9b13a26b634f87c6be4642d89bd242358",
  "cloud":"ubuntu-24.04-server-cloudimg-amd64.img",
  "cloud_sha":"d1940f7d69d343355e183dff1e08a59852d32e7309baa7a4bad8365b11b005ac",
  "firefox_platform":"linux-x86_64",
  "gecko_asset":f"geckodriver-v{GECKO_VERSION}-linux64.tar.gz"},
 "arm64":{
  "rootfs":"ubuntu-24.04-server-cloudimg-arm64-root.tar.xz",
  "rootfs_sha":"154c979c389e90ae676b420326e73eb8fb6b88ef94da21f523b4069410e1d154",
  "cloud":"ubuntu-24.04-server-cloudimg-arm64.img",
  "cloud_sha":"2eaec7286c49fdea713dddabcf5012cafa7097a658e916acb48f4bc5fdc8e419",
  "firefox_platform":"linux-aarch64",
  "gecko_asset":f"geckodriver-v{GECKO_VERSION}-linux-aarch64.tar.gz"}
}

DOCKERFILE='''ARG ROOTFS
FROM scratch
ARG ROOTFS
ADD ${ROOTFS} /
ARG TARGETARCH
ARG QIKVRT_VERSION
LABEL org.opencontainers.image.title="QIK-VRT Mesh Linux Appliance"
LABEL org.opencontainers.image.version="${QIKVRT_VERSION}"
LABEL org.opencontainers.image.source="https://github.com/Goldkelch/qik-vrt"
ENV DEBIAN_FRONTEND=noninteractive DISPLAY=:99 QIKVRT_HOME=/opt/qikvrt
ENV QIKVRT_EFFECT_ACK_SCOPE=BOUNDED_LOOPBACK_TERMINAL_INPUT_ONLY QIKVRT_EXTERNAL_EFFECT=NONE
RUN apt-get update && apt-get install -y --no-install-recommends bash ca-certificates curl jq python3 python3-minimal xvfb x11vnc openbox novnc websockify libgtk-3-0 libdbus-glib-1-2 libasound2t64 libx11-xcb1 libxt6 libpci3 libgl1 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libxkbcommon0 libxshmfence1 libnss3 libnspr4 fonts-dejavu-core zip unzip tini && rm -rf /var/lib/apt/lists/*
COPY root/ /
RUN chmod 0755 /usr/local/bin/qikvrt-mesh-entrypoint /usr/local/bin/qikvrt-launch-firefox /usr/local/bin/qikvrt-appliance-selftest && mkdir -p /var/lib/qikvrt /var/log/qikvrt /run/qikvrt && useradd --create-home --home-dir /home/qikvrt --shell /bin/bash qikvrt && chown -R qikvrt:qikvrt /var/lib/qikvrt /var/log/qikvrt /run/qikvrt /home/qikvrt /opt/qikvrt
USER qikvrt
WORKDIR /opt/qikvrt
EXPOSE 6080
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 CMD curl --fail --silent http://127.0.0.1:8771/.well-known/effect-ack >/dev/null || exit 1
ENTRYPOINT ["/usr/bin/tini","--","/usr/local/bin/qikvrt-mesh-entrypoint"]
'''
ENTRYPOINT='''#!/usr/bin/env bash
set -euo pipefail
mkdir -p /run/qikvrt /var/log/qikvrt "$HOME/qikvrt-gecko-profiles"
python3 -B /opt/qikvrt/effect-ack-profile/src/qikvrt_effect_ack_http_terminal.py > /var/log/qikvrt/effect-ack-backend.log 2>&1 &
for _ in $(seq 1 200); do
  if curl --fail --silent http://127.0.0.1:8771/.well-known/effect-ack >/run/qikvrt/discovery.json 2>/dev/null; then break; fi
  sleep 0.1
done
curl --fail --silent http://127.0.0.1:8771/.well-known/effect-ack >/dev/null
Xvfb :99 -screen 0 1280x800x24 -nolisten tcp > /var/log/qikvrt/xvfb.log 2>&1 &
openbox-session > /var/log/qikvrt/openbox.log 2>&1 &
x11vnc -display :99 -forever -shared -nopw -rfbport 5900 > /var/log/qikvrt/x11vnc.log 2>&1 &
websockify --web=/usr/share/novnc/ 0.0.0.0:6080 127.0.0.1:5900 > /var/log/qikvrt/novnc.log 2>&1 &
exec /usr/local/bin/qikvrt-launch-firefox --firefox /opt/firefox/firefox --geckodriver /opt/geckodriver/geckodriver --xpi /opt/qikvrt/qikvrt-terminal.xpi --receipt /var/lib/qikvrt/firefox-effect-ack-receipt.json --profile-root "$HOME/qikvrt-gecko-profiles"
'''
LAUNCH_FIREFOX=r'''#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,subprocess,time,urllib.request
from pathlib import Path
from typing import Any
EXTENSION_ID="qikvrt-ai-terminal@goldkelch.local"
UUID="7d844896-31c8-4a82-8c53-98e473a668c7"
def request(method:str,url:str,body:dict[str,Any]|None=None,timeout:float=30.0)->dict[str,Any]:
 data=None if body is None else json.dumps(body).encode(); req=urllib.request.Request(url,data=data,method=method)
 if data is not None:req.add_header("Content-Type","application/json")
 with urllib.request.urlopen(req,timeout=timeout) as r: raw=r.read()
 return json.loads(raw.decode()) if raw else {"value":None}
def execute(base:str,session:str,script:str)->Any:return request("POST",f"{base}/session/{session}/execute/sync",{"script":script,"args":[]}).get("value")
def main()->int:
 p=argparse.ArgumentParser(); p.add_argument("--firefox",required=True);p.add_argument("--geckodriver",required=True);p.add_argument("--xpi",type=Path,required=True);p.add_argument("--receipt",type=Path,required=True);p.add_argument("--profile-root",type=Path,required=True);a=p.parse_args()
 a.profile_root.mkdir(parents=True,exist_ok=True);base="http://127.0.0.1:4444";log=open("/var/log/qikvrt/geckodriver.log","wb");proc=subprocess.Popen([a.geckodriver,"--host","127.0.0.1","--port","4444","--profile-root",str(a.profile_root),"--allow-system-access"],stdout=log,stderr=subprocess.STDOUT);session=None
 try:
  for _ in range(200):
   try:
    if request("GET",base+"/status",timeout=1).get("value",{}).get("ready") is True:break
   except Exception:pass
   time.sleep(.1)
  else:raise RuntimeError("geckodriver did not become ready")
  created=request("POST",base+"/session",{"capabilities":{"alwaysMatch":{"browserName":"firefox","moz:firefoxOptions":{"binary":a.firefox,"prefs":{"extensions.webextensions.uuids":json.dumps({EXTENSION_ID:UUID},separators=(",",":")),"browser.shell.checkDefaultBrowser":False,"browser.tabs.warnOnClose":False}}}}},timeout=90);value=created.get("value") or {};session=value.get("sessionId") or created.get("sessionId")
  if not session:raise RuntimeError(f"Firefox session unavailable: {created}")
  addon=request("POST",f"{base}/session/{session}/moz/addon/install",{"path":str(a.xpi.resolve()),"temporary":True}).get("value")
  if addon!=EXTENSION_ID:raise RuntimeError(f"unexpected extension id {addon!r}")
  request("POST",f"{base}/session/{session}/moz/context",{"context":"chrome"});raw=execute(base,session,"return Services.prefs.getStringPref('extensions.webextensions.uuids', '{}');");request("POST",f"{base}/session/{session}/moz/context",{"context":"content"});uuid=json.loads(str(raw or "{}"))[EXTENSION_ID]
  request("POST",f"{base}/session/{session}/url",{"url":f"moz-extension://{uuid}/options.html?qikvrt_e2e=1"})
  status=""
  for _ in range(300):
   status=str(execute(base,session,"return document.getElementById('status') ? document.getElementById('status').textContent : '';") or "")
   if status.startswith("E2E_DONE:") or status.startswith("E2E_FAIL:"):break
   time.sleep(.1)
  if not status.startswith("E2E_DONE:"):raise RuntimeError(status or "bounded E2E did not complete")
  page=json.loads(status.split(":",1)[1]);state=json.load(urllib.request.urlopen("http://127.0.0.1:8771/terminal/state"));receipt={"schema":"qikvrt_mesh_linux_firefox_effect_ack_receipt_v1","release_version":os.environ.get("QIKVRT_VERSION","1.0.0"),"firefox_terminal_execution_observed":True,"bounded_loopback_effect_ack_done":True,"effect_ack_done_scope":"BOUNDED_LOOPBACK_TERMINAL_INPUT_ONLY","external_effect":"NONE","extension_id":addon,"extension_uuid":uuid,"page":page,"backend_state":state,"physical_megast_execution":False,"general_internet_reachability_claimed":False};a.receipt.parent.mkdir(parents=True,exist_ok=True);a.receipt.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n");print(json.dumps(receipt,sort_keys=True),flush=True)
  while True:time.sleep(5);execute(base,session,"return document.readyState;")
 finally:
  if session:
   try:request("DELETE",f"{base}/session/{session}",timeout=5)
   except Exception:pass
  proc.terminate();log.close()
if __name__=="__main__":raise SystemExit(main())
'''
SELFTEST='''#!/usr/bin/env bash
set -euo pipefail
/opt/firefox/firefox --version
/opt/geckodriver/geckodriver --version
python3 -c 'import pathlib,sys;[compile(pathlib.Path(p).read_text(encoding="utf-8"),p,"exec") for p in sys.argv[1:]]' /opt/qikvrt/effect-ack-profile/src/qikvrt_effect_ack_http_terminal.py /usr/local/bin/qikvrt-launch-firefox
test -s /opt/qikvrt/qikvrt-terminal.xpi
test -f /opt/qikvrt/source/src/effect_ack_core.c
test -f /opt/qikvrt/atari-browser-c89/src/atari_browser_c89.c
test -f /opt/qikvrt/autonomous-repair/tools/qikvrt_autonomous_problem_solver.py
echo QIKVRT_MESH_LINUX_SELFTEST=OK
'''
SERVICE='''[Unit]
Description=QIK-VRT Mesh Linux Firefox/Effect-Ack appliance
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target
[Service]
Type=simple
Restart=always
RestartSec=5
ExecStartPre=-/usr/bin/docker rm -f qikvrt-mesh-linux
ExecStartPre=/usr/bin/docker load -i /opt/qikvrt/qikvrt-mesh-linux.oci.tar
ExecStart=/usr/bin/docker run --rm --name qikvrt-mesh-linux --network host qikvrt-mesh-linux:1.0.0
ExecStop=/usr/bin/docker stop qikvrt-mesh-linux
[Install]
WantedBy=multi-user.target
'''
APPLIANCE_TEXT='''QIK-VRT Mesh Linux 1.0.0
Firefox/noVNC: http://<vm-address>:6080/vnc.html
Effect-Ack backend: loopback-only
'''
FIRSTBOOT=f'''#!/usr/bin/env bash
set -euo pipefail
systemctl enable docker
systemctl enable qikvrt-mesh.service
install -d -m 0755 /etc/qikvrt
cat > /etc/qikvrt/APPLIANCE.txt <<'QIKVRT_APPLIANCE_EOF'
{APPLIANCE_TEXT}QIKVRT_APPLIANCE_EOF
'''
OVF='''<?xml version="1.0" encoding="UTF-8"?>
<Envelope ovf:version="2.0" xmlns="http://schemas.dmtf.org/ovf/envelope/1" xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData" xmlns:vssd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData"><References><File ovf:id="file1" ovf:href="qikvrt-mesh-linux-1.0.0-amd64.vmdk" ovf:size="__VMDK_SIZE__"/></References><DiskSection><Info>Virtual disk</Info><Disk ovf:diskId="disk1" ovf:fileRef="file1" ovf:capacity="20" ovf:capacityAllocationUnits="byte * 2^30" ovf:format="http://www.vmware.com/interfaces/specifications/vmdk.html#streamOptimized"/></DiskSection><NetworkSection><Info>Networks</Info><Network ovf:name="NAT"><Description>NAT</Description></Network></NetworkSection><VirtualSystem ovf:id="qikvrt-mesh-linux-1.0.0"><Info>QIK-VRT Mesh Linux</Info><Name>QIK-VRT Mesh Linux 1.0.0</Name><OperatingSystemSection ovf:id="94"><Info>Ubuntu Linux 64-bit</Info></OperatingSystemSection><VirtualHardwareSection><Info>Virtual hardware</Info><System><vssd:ElementName>Virtual Hardware Family</vssd:ElementName><vssd:InstanceID>0</vssd:InstanceID><vssd:VirtualSystemIdentifier>QIK-VRT Mesh Linux</vssd:VirtualSystemIdentifier><vssd:VirtualSystemType>vmx-19</vssd:VirtualSystemType></System><Item><rasd:ElementName>2 CPUs</rasd:ElementName><rasd:InstanceID>1</rasd:InstanceID><rasd:ResourceType>3</rasd:ResourceType><rasd:VirtualQuantity>2</rasd:VirtualQuantity></Item><Item><rasd:ElementName>4096 MB</rasd:ElementName><rasd:InstanceID>2</rasd:InstanceID><rasd:ResourceType>4</rasd:ResourceType><rasd:VirtualQuantity>4096</rasd:VirtualQuantity></Item><Item><rasd:Address>0</rasd:Address><rasd:ElementName>SATA</rasd:ElementName><rasd:InstanceID>3</rasd:InstanceID><rasd:ResourceSubType>AHCI</rasd:ResourceSubType><rasd:ResourceType>20</rasd:ResourceType></Item><Item><rasd:AddressOnParent>0</rasd:AddressOnParent><rasd:ElementName>Disk 1</rasd:ElementName><rasd:HostResource>ovf:/disk/disk1</rasd:HostResource><rasd:InstanceID>4</rasd:InstanceID><rasd:Parent>3</rasd:Parent><rasd:ResourceType>17</rasd:ResourceType></Item><Item><rasd:AutomaticAllocation>true</rasd:AutomaticAllocation><rasd:Connection>NAT</rasd:Connection><rasd:ElementName>Ethernet</rasd:ElementName><rasd:InstanceID>5</rasd:InstanceID><rasd:ResourceType>10</rasd:ResourceType></Item></VirtualHardwareSection></VirtualSystem></Envelope>
'''

def run(*args:str,cwd:Path|None=None,env:dict[str,str]|None=None,capture=False)->str:
 cp=subprocess.run(args,cwd=cwd,env=env,text=True,check=True,stdout=subprocess.PIPE if capture else None)
 return cp.stdout.strip() if capture else ""
def sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open("rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
 return h.hexdigest()
def download(url:str,path:Path)->None:path.parent.mkdir(parents=True,exist_ok=True);run("curl","--fail","--location","--retry","4","--retry-all-errors",url,"-o",str(path))
def verify(path:Path,expected:str)->None:
 actual=sha256(path)
 if actual!=expected:raise SystemExit(f"SHA256 mismatch for {path}: {actual} != {expected}")
def write(path:Path,text:str,executable=False)->None:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text);path.chmod(0o755 if executable else 0o644)
def libguestfs_clock_sync_command()->str:
 anchor_text=os.environ.get("QIKVRT_TRUSTED_HOST_EPOCH","")
 if not anchor_text.isdecimal():raise SystemExit("trusted runner UTC epoch is missing or invalid")
 anchor=int(anchor_text);now=int(time.time())
 if not UBUNTU_RELEASE_MIN_EPOCH<=anchor<=MAX_SUPPORTED_BUILD_EPOCH:raise SystemExit(f"trusted runner UTC epoch outside supported build window: {anchor}")
 if not anchor-TRUSTED_HOST_EPOCH_BACKWARD_SKEW_SECONDS<=now<=anchor+TRUSTED_HOST_EPOCH_MAX_AGE_SECONDS:raise SystemExit(f"runner UTC epoch escaped trusted post-APT anchor: {now}")
 target=now+CLOCK_CUSHION_SECONDS;latest=target+CLOCK_OBSERVATION_WINDOW_SECONDS
 if latest>MAX_SUPPORTED_BUILD_EPOCH:raise SystemExit(f"cushioned appliance UTC epoch exceeds supported build window: {target}")
 return f"set -eu; date -u -s '@{target}' >/dev/null; now=$(date -u +%s); [ \"$now\" -ge {target} ]; [ \"$now\" -le {latest} ]; check_date=true; check_valid_until=true; apt_get_check_date=true; apt_get_check_valid_until=true; apt_values=$(apt-config shell check_date Acquire::Check-Date/b check_valid_until Acquire::Check-Valid-Until/b apt_get_check_date Binary::apt-get::Acquire::Check-Date/b apt_get_check_valid_until Binary::apt-get::Acquire::Check-Valid-Until/b); eval \"$apt_values\"; if [ \"$check_date\" != true ] || [ \"$check_valid_until\" != true ] || [ \"$apt_get_check_date\" != true ] || [ \"$apt_get_check_valid_until\" != true ]; then echo 'BLOCK: guest APT date verification is disabled' >&2; exit 22; fi; apt_source_date_override_regex='{APT_SOURCE_DATE_OVERRIDE_REGEX}'; set +e; grep -ERisq --include='sources.list' --include='*.list' --include='*.sources' \"$apt_source_date_override_regex\" /etc/apt; apt_source_status=$?; set -e; case \"$apt_source_status\" in 0) echo 'BLOCK: guest APT source contains a per-source date-verification override' >&2; exit 22 ;; 1) ;; *) echo 'BLOCK: guest APT source date-verification configuration could not be read' >&2; exit 22 ;; esac; echo QIKVRT_LIBGUESTFS_CLOCK_SYNC=OK"
def create_expanded_cloud_image(cloud:Path,qcow:Path,env:dict[str,str])->None:
 run("qemu-img","create","-f","qcow2","-o","preallocation=metadata",str(qcow),str(VM_DISK_SIZE_BYTES),env=env)
 run("virt-resize","--format","qcow2","--output-format","qcow2","--expand",UBUNTU_CLOUD_ROOT_PARTITION,str(cloud),str(qcow),env=env)
def vm_payload_validation_command(oci_bytes:int)->str:
 if oci_bytes<=0:raise ValueError("VM OCI payload size must be positive")
 return f"set -eu; root_blocks=$(stat -f -c %b /); root_block_size=$(stat -f -c %S /); case \"$root_blocks:$root_block_size\" in *[!0-9:]*) exit 23 ;; esac; root_bytes=$((root_blocks * root_block_size)); [ \"$root_bytes\" -ge {VM_ROOT_FILESYSTEM_MIN_BYTES} ]; test \"$(stat -c %s /opt/qikvrt/qikvrt-mesh-linux.oci.tar)\" -eq {oci_bytes}; test -s /etc/systemd/system/qikvrt-mesh.service; test -x /usr/local/sbin/qikvrt-firstboot; test -s /etc/qikvrt/APPLIANCE.txt; systemctl is-enabled --quiet docker.service; systemctl is-enabled --quiet qikvrt-mesh.service; printf '%s\\n' '{VM_PAYLOAD_RECEIPT}' > {VM_PAYLOAD_RECEIPT_PATH}"
def vm_payload_readback_command(oci:Path,service:Path,first:Path)->str:
 files=[(oci,"/opt/qikvrt/qikvrt-mesh-linux.oci.tar"),(service,"/etc/systemd/system/qikvrt-mesh.service"),(first,"/usr/local/sbin/qikvrt-firstboot")]
 checks=[]
 for host,guest in files:
  if not host.is_file() or host.stat().st_size<=0:raise ValueError(f"VM payload source is missing or empty: {host}")
  checks.append(f"test \"$(stat -c %s {guest})\" -eq {host.stat().st_size}; printf '%s  %s\\n' '{sha256(host)}' '{guest}' | sha256sum --check --strict - >/dev/null")
 appliance_bytes=len(APPLIANCE_TEXT.encode());appliance_sha=hashlib.sha256(APPLIANCE_TEXT.encode()).hexdigest()
 checks.append(f"test \"$(stat -c %s /etc/qikvrt/APPLIANCE.txt)\" -eq {appliance_bytes}; printf '%s  %s\\n' '{appliance_sha}' '/etc/qikvrt/APPLIANCE.txt' | sha256sum --check --strict - >/dev/null")
 checks.extend([f"test \"$(cat {VM_PAYLOAD_RECEIPT_PATH})\" = '{VM_PAYLOAD_RECEIPT}'","systemctl is-enabled --quiet docker.service","systemctl is-enabled --quiet qikvrt-mesh.service",f"printf '%s\\n' '{VM_PAYLOAD_RECEIPT}'"])
 return f"set -eu; root_blocks=$(stat -f -c %b /); root_block_size=$(stat -f -c %S /); case \"$root_blocks:$root_block_size\" in *[!0-9:]*) exit 23 ;; esac; root_bytes=$((root_blocks * root_block_size)); [ \"$root_bytes\" -ge {VM_ROOT_FILESYSTEM_MIN_BYTES} ]; "+"; ".join(checks)
def validate_vm_payload_readback(qcow:Path,oci:Path,service:Path,first:Path,env:dict[str,str])->None:
 command=vm_payload_readback_command(oci,service,first)
 observed=run("guestfish","--ro","--format=qcow2","-a",str(qcow),"-i","sh",command,env=env,capture=True)
 if observed!=VM_PAYLOAD_RECEIPT:raise RuntimeError(f"VM payload receipt mismatch: {observed!r}")
 print(VM_PAYLOAD_RECEIPT,flush=True)
def archive(commit:str,paths:list[str],target:Path)->None:
 target.mkdir(parents=True,exist_ok=True);p1=subprocess.Popen(["git","archive",commit,*paths],stdout=subprocess.PIPE);subprocess.run(["tar","-x","-C",str(target)],stdin=p1.stdout,check=True);assert p1.stdout is not None;p1.stdout.close()
 if p1.wait()!=0:raise SystemExit(f"git archive failed: {commit}")
def prepare(context:Path,downloads:Path,cfg:dict[str,str])->tuple[str,str]:
 run("git","fetch","--no-tags","--depth=1","origin",FIREFOX_EFFECT_SHA,ATARI_BROWSER_SHA,AUTONOMOUS_REPAIR_SHA)
 archive("HEAD",["."],context/"root/opt/qikvrt/source")
 effect=context/"root/opt/qikvrt/effect-ack-profile";archive(FIREFOX_EFFECT_SHA,["browser/firefox/qikvrt-terminal","src/qikvrt_effect_ack_http_terminal.py","tools/qikvrt_firefox_terminal_e2e.py","policy/MLP_FIREFOX_EFFECT_ACK_E2E_V1.json","tests/test_qikvrt_effect_ack_http_terminal.py","tests/test_qikvrt_firefox_terminal_e2e_contract.py"],effect)
 archive(ATARI_BROWSER_SHA,["browser/atari-c89","include/qikvrt/atari_browser_c89.h","runtime/atari-megast/qikbrow.c","src/atari_browser_c89.c","tests/test_atari_browser_c89.c","tests/test_atari_browser_c89.sh","tests/test_qikvrt_atari_browser_c89_contract.py"],context/"root/opt/qikvrt/atari-browser-c89")
 archive(AUTONOMOUS_REPAIR_SHA,[".github/workflows/qikvrt_mesh_autonomous_repair.yml","tools/qikvrt_autonomous_problem_solver.py","tests/test_qikvrt_autonomous_problem_solver.py","policy/MESH_AUTONOMOUS_DETERMINISTIC_REPAIR_V1.json","docs/MESH_AUTONOMOUS_DETERMINISTIC_REPAIR_V1.md"],context/"root/opt/qikvrt/autonomous-repair")
 run("zip","-qr",str(context/"root/opt/qikvrt/qikvrt-terminal.xpi"),".",cwd=effect/"browser/firefox/qikvrt-terminal")
 rootfs=downloads/cfg["rootfs"];download(f"{UBUNTU_BASE}/{cfg['rootfs']}",rootfs);verify(rootfs,cfg["rootfs_sha"]);shutil.copy2(rootfs,context/cfg["rootfs"])
 mozilla=f"https://ftp.mozilla.org/pub/firefox/releases/{FIREFOX_VERSION}";key=downloads/"KEY";sums=downloads/"SHA256SUMS";sig=downloads/"SHA256SUMS.asc";download(f"{mozilla}/KEY",key);download(f"{mozilla}/SHA256SUMS",sums);download(f"{mozilla}/SHA256SUMS.asc",sig);gnupg=downloads/"gnupg";gnupg.mkdir(mode=0o700);env={**os.environ,"GNUPGHOME":str(gnupg)};run("gpg","--batch","--import",str(key),env=env);run("gpg","--batch","--verify",str(sig),str(sums),env=env)
 name=f"firefox-{FIREFOX_VERSION}.tar.xz";rel=f"{cfg['firefox_platform']}/en-US/{name}";fsha=next(line.split()[0] for line in sums.read_text().splitlines() if len(line.split())>=2 and line.split()[-1]==rel);fa=downloads/name;download(f"{mozilla}/{rel}",fa);verify(fa,fsha);run("tar","-xJf",str(fa),"-C",str(context/"root/opt"))
 rj=downloads/"gecko.json";download(f"https://api.github.com/repos/mozilla/geckodriver/releases/tags/v{GECKO_VERSION}",rj);data=json.loads(rj.read_text());asset=next(x for x in data["assets"] if x["name"]==cfg["gecko_asset"]);gsha=asset["digest"].split(":",1)[1];ga=downloads/cfg["gecko_asset"];download(asset["browser_download_url"],ga);verify(ga,gsha);gd=context/"root/opt/geckodriver";gd.mkdir(parents=True);run("tar","-xzf",str(ga),"-C",str(gd));return fsha,gsha
def build(arch:str,output:Path)->None:
 cfg=ARCH[arch];work=Path(os.environ.get("RUNNER_TEMP","/tmp"))/f"qikvrt-mesh-linux-{arch}";shutil.rmtree(work,ignore_errors=True);context=work/"context";downloads=work/"downloads";dist=work/"dist"
 for p in [context/"root/opt/qikvrt",context/"root/usr/local/bin",downloads,dist,output]:p.mkdir(parents=True,exist_ok=True)
 fsha,gsha=prepare(context,downloads,cfg);write(context/"Dockerfile",DOCKERFILE);write(context/"root/usr/local/bin/qikvrt-mesh-entrypoint",ENTRYPOINT,True);write(context/"root/usr/local/bin/qikvrt-launch-firefox",LAUNCH_FIREFOX,True);write(context/"root/usr/local/bin/qikvrt-appliance-selftest",SELFTEST,True)
 image=f"qikvrt-mesh-linux:{VERSION}";run("docker","build","--platform",f"linux/{arch}","--build-arg",f"ROOTFS={cfg['rootfs']}","--build-arg",f"TARGETARCH={arch}","--build-arg",f"QIKVRT_VERSION={VERSION}","-t",image,str(context));run("docker","run","--rm","--platform",f"linux/{arch}","--entrypoint","/usr/local/bin/qikvrt-appliance-selftest",image)
 oci=dist/f"qikvrt-mesh-linux-{VERSION}-{arch}.oci.tar";run("docker","save",image,"-o",str(oci));run("zstd","-T0","-19","--rm",str(oci));cloud=downloads/cfg["cloud"];download(f"{UBUNTU_BASE}/{cfg['cloud']}",cloud);verify(cloud,cfg["cloud_sha"]);qcow=dist/f"qikvrt-mesh-linux-{VERSION}-{arch}.qcow2";env={**os.environ,"LIBGUESTFS_BACKEND":"direct","LIBGUESTFS_DEBUG":"1","LIBGUESTFS_TRACE":"1"};create_expanded_cloud_image(cloud,qcow,env);cloud.unlink();plain=work/"qikvrt-mesh-linux.oci.tar";run("zstd","-d",str(oci)+".zst","-o",str(plain));service=work/"qikvrt-mesh.service";first=work/"qikvrt-firstboot";write(service,SERVICE);write(first,FIRSTBOOT,True);clock_sync=libguestfs_clock_sync_command();payload_validation=vm_payload_validation_command(plain.stat().st_size);run("virt-customize","--network","-a",str(qcow),"--run-command",clock_sync,"--install","docker.io","--mkdir","/opt/qikvrt","--copy-in",f"{plain}:/opt/qikvrt","--copy-in",f"{service}:/etc/systemd/system","--copy-in",f"{first}:/usr/local/sbin","--run-command","chmod 0755 /usr/local/sbin/qikvrt-firstboot","--run-command","/usr/local/sbin/qikvrt-firstboot","--run-command","truncate -s 0 /etc/machine-id","--run-command",payload_validation,"--selinux-relabel",env=env);validate_vm_payload_readback(qcow,plain,service,first,env);run("qemu-img","check",str(qcow));qcopy=work/f"{arch}.qcow2";shutil.copy2(qcow,qcopy);run("zstd","-T0","-19","--rm",str(qcopy));shutil.move(str(qcopy)+".zst",str(qcow)+".zst");vhdx=dist/f"qikvrt-mesh-linux-{VERSION}-{arch}.vhdx";run("qemu-img","convert","-p","-O","vhdx","-o","subformat=dynamic",str(qcow),str(vhdx));run("zstd","-T0","-19","--rm",str(vhdx))
 if arch=="amd64":
  vmdk=dist/f"qikvrt-mesh-linux-{VERSION}-amd64.vmdk";run("qemu-img","convert","-p","-O","vmdk","-o","subformat=streamOptimized",str(qcow),str(vmdk));ovf=dist/f"qikvrt-mesh-linux-{VERSION}-amd64.ovf";write(ovf,OVF.replace("__VMDK_SIZE__",str(vmdk.stat().st_size)));run("tar","-cf",str(dist/f"qikvrt-mesh-linux-{VERSION}-amd64.ova"),ovf.name,vmdk.name,cwd=dist);ovf.unlink();vmdk.unlink()
 qcow.unlink()
 if arch=="amd64":shutil.copy2(context/"root/opt/qikvrt/qikvrt-terminal.xpi",dist/f"qikvrt-terminal-{VERSION}.xpi")
 receipt={"schema":"qikvrt_mesh_linux_arch_build_receipt_v1","version":VERSION,"architecture":arch,"authority_base":AUTHORITY_BASE,"release_source_head":run("git","rev-parse","HEAD",capture=True),"release_source_tree":run("git","rev-parse","HEAD^{tree}",capture=True),"firefox_effect_ack_source_head":FIREFOX_EFFECT_SHA,"atari_browser_c89_source_head":ATARI_BROWSER_SHA,"autonomous_repair_source_head":AUTONOMOUS_REPAIR_SHA,"ubuntu_release":UBUNTU_RELEASE,"ubuntu_rootfs_sha256":cfg["rootfs_sha"],"ubuntu_cloud_image_sha256":cfg["cloud_sha"],"firefox_version":FIREFOX_VERSION,"firefox_archive_sha256":fsha,"geckodriver_version":GECKO_VERSION,"geckodriver_archive_sha256":gsha,"effect_ack_scope":"BOUNDED_LOOPBACK_TERMINAL_INPUT_ONLY","external_effect":"NONE","physical_megast_execution_claimed":False,"general_internet_reachability_claimed":False,"pass":False,"final_pass":False};write(dist/f"qikvrt-mesh-linux-{VERSION}-{arch}.build.json",json.dumps(receipt,sort_keys=True,indent=2)+"\n");write(dist/f"SHA256SUMS-{arch}","".join(f"{sha256(p)}  {p.name}\n" for p in sorted(dist.iterdir()) if p.is_file()))
 for p in dist.iterdir():shutil.copy2(p,output/p.name)
def manifest(assets:Path,image:str,image_digest:str,head:str,tree:str,output:Path)->None:
 items=[{"name":p.name,"bytes":p.stat().st_size,"sha256":sha256(p)} for p in sorted(assets.iterdir()) if p.is_file() and p.name not in {output.name,"SHA256SUMS"}];obj={"schema":"qikvrt_mesh_linux_release_manifest_v1","version":VERSION,"tag":"qikvrt-mesh-linux-v1.0.0","source_head":head,"source_tree":tree,"oci_image":image,"oci_image_digest":image_digest,"effect_ack_scope":"BOUNDED_LOOPBACK_TERMINAL_INPUT_ONLY","external_effect":"NONE","assets":items,"physical_megast_execution_claimed":False,"general_internet_reachability_claimed":False,"general_effect_ack_done_claimed":False,"pass":False,"final_pass":False};write(output,json.dumps(obj,sort_keys=True,indent=2)+"\n")
def main()->int:
 p=argparse.ArgumentParser();s=p.add_subparsers(dest="cmd",required=True);b=s.add_parser("build");b.add_argument("--arch",choices=ARCH,required=True);b.add_argument("--output",type=Path,required=True);m=s.add_parser("manifest");m.add_argument("--assets",type=Path,required=True);m.add_argument("--image",required=True);m.add_argument("--image-digest",required=True);m.add_argument("--head",required=True);m.add_argument("--tree",required=True);m.add_argument("--output",type=Path,required=True);a=p.parse_args();build(a.arch,a.output) if a.cmd=="build" else manifest(a.assets,a.image,a.image_digest,a.head,a.tree,a.output);return 0
if __name__=="__main__":raise SystemExit(main())
