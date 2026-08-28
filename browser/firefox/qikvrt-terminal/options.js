const fields = ["accent", "fontScale", "density", "position"];
const peerFields = ["peerV2Backend", "peerV2SourceNode", "peerV2TargetNode", "peerV2TargetEndpoint", "peerV2ResponsibilityOwner"];

async function load() {
  const stored = await browser.storage.local.get(["qikvrtTerminalPreferences", "qikvrtPeerV2Config"]);
  const p = stored.qikvrtTerminalPreferences || {};
  for (const id of fields) if (p[id] !== undefined) document.getElementById(id).value = p[id];
  const peer = stored.qikvrtPeerV2Config || {};
  document.getElementById("peerV2Enabled").checked = peer.enabled === true;
  const mapping = {
    peerV2Backend: "backend",
    peerV2SourceNode: "source_node_id",
    peerV2TargetNode: "target_node_id",
    peerV2TargetEndpoint: "target_endpoint_id",
    peerV2ResponsibilityOwner: "responsibility_owner"
  };
  for (const id of peerFields) if (peer[mapping[id]] !== undefined) document.getElementById(id).value = peer[mapping[id]];
}

async function save() {
  const value = {};
  for (const id of fields) value[id] = document.getElementById(id).value;
  value.fontScale = Number(value.fontScale);
  const peer = {
    enabled: document.getElementById("peerV2Enabled").checked,
    backend: document.getElementById("peerV2Backend").value,
    source_node_id: document.getElementById("peerV2SourceNode").value.trim(),
    target_node_id: document.getElementById("peerV2TargetNode").value.trim(),
    target_endpoint_id: document.getElementById("peerV2TargetEndpoint").value.trim(),
    responsibility_owner: document.getElementById("peerV2ResponsibilityOwner").value
  };
  await browser.storage.local.set({qikvrtTerminalPreferences: value, qikvrtPeerV2Config: peer});
  document.getElementById("status").textContent = "gespeichert";
}

document.getElementById("save").addEventListener("click", () => save().catch(error => {
  document.getElementById("status").textContent = error.message;
}));
load();
