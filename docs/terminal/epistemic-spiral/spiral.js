(() => {
  "use strict";
  const expected = ["ar","de","en","es","fr","hi","id","it","ja","ko","pt_BR","ru","tr","zh_CN"];
  const $ = s => document.querySelector(s);
  let catalog = null;
  let running = !matchMedia("(prefers-reduced-motion: reduce)").matches;

  function bestLocale() {
    const raw = (navigator.language || "en").replace("-", "_");
    if (expected.includes(raw)) return raw;
    const base = raw.split("_")[0];
    return expected.find(x => x.split("_")[0] === base) || "en";
  }

  function apply(locale) {
    const t = catalog.locales[locale] || catalog.locales.en;
    document.documentElement.lang = locale.replace("_","-");
    document.documentElement.dir = locale === "ar" ? "rtl" : "ltr";
    for (const node of document.querySelectorAll("[data-i18n]")) {
      const key = node.dataset.i18n;
      if (Object.prototype.hasOwnProperty.call(t,key)) node.textContent = t[key];
    }
    $("#locale").value = locale;
    localStorage.setItem("qikvrtSpiralLocale", locale);
    syncMotionLabel();
  }

  function syncMotionLabel() {
    if (!catalog) return;
    const locale = $("#locale").value || "en";
    const t = catalog.locales[locale] || catalog.locales.en;
    $("#motion").textContent = running ? t.pause : t.play;
    document.body.classList.toggle("paused", !running);
  }

  async function boot() {
    const [locResponse,stateResponse] = await Promise.all([
      fetch("locales.json",{cache:"no-store"}),
      fetch("state.json",{cache:"no-store"})
    ]);
    if (!locResponse.ok || !stateResponse.ok) throw new Error("QIK-VRT spiral assets unavailable");
    catalog = await locResponse.json();
    const state = await stateResponse.json();
    if (catalog.schema !== "qikvrt_epistemic_spiral_locales_v1") throw new Error("locale schema mismatch");
    if (state.schema !== "qikvrt_epistemic_spiral_state_v1") throw new Error("state schema mismatch");
    const actual = Object.keys(catalog.locales).sort();
    if (JSON.stringify(actual) !== JSON.stringify([...expected].sort())) throw new Error("locale coverage mismatch");

    const select = $("#locale");
    for (const id of expected) {
      const option = document.createElement("option");
      option.value = id;
      option.textContent = catalog.locales[id].name;
      select.appendChild(option);
    }
    const chosen = localStorage.getItem("qikvrtSpiralLocale");
    apply(expected.includes(chosen) ? chosen : bestLocale());
    select.addEventListener("change", () => apply(select.value));
    $("#motion").addEventListener("click", () => { running = !running; syncMotionLabel(); });
  }

  boot().catch(error => {
    document.body.classList.add("paused");
    const target = document.querySelector(".boundary");
    if (target) target.textContent = "HOLD · " + error.message;
  });
})();