const fields = ["accent", "fontScale", "density", "position"];

async function load() {
  const stored = await browser.storage.local.get("qikvrtTerminalPreferences");
  const p = stored.qikvrtTerminalPreferences || {};
  for (const id of fields) if (p[id] !== undefined) document.getElementById(id).value = p[id];
}

async function save() {
  const value = {};
  for (const id of fields) value[id] = document.getElementById(id).value;
  value.fontScale = Number(value.fontScale);
  await browser.storage.local.set({qikvrtTerminalPreferences: value});
  document.getElementById("status").textContent = "gespeichert";
}

document.getElementById("save").addEventListener("click", () => save().catch(error => {
  document.getElementById("status").textContent = error.message;
}));
load();
