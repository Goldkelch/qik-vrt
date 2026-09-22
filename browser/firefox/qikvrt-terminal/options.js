const fields = ["accent", "fontScale", "density", "position"];
const message = name => browser.i18n.getMessage(name);
document.documentElement.lang = message("@@ui_locale").replaceAll("_", "-");
document.documentElement.dir = message("@@bidi_dir");
document.title = `QIKVRT AI Terminal · ${message("personalize")}`;
document.querySelectorAll("[data-i18n]").forEach(node => {
  node.textContent = message(node.dataset.i18n);
});

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
  document.getElementById("status").textContent = message("saved");
}

document.getElementById("save").addEventListener("click", () => save().catch(error => {
  document.getElementById("status").textContent = error.message;
}));
load();
