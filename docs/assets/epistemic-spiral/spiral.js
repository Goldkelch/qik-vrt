(()=>{"use strict";
const root=document.querySelector("[data-qikvrt-spiral]");if(!root)return;
const select=root.querySelector("[data-role=locale]");
const title=root.querySelector("[data-role=title]");
const subtitle=root.querySelector("[data-role=subtitle]");
const explanation=root.querySelector("[data-role=explanation]");
const cosmos=root.querySelector("[data-role=cosmos]");
const boundary=root.querySelector("[data-role=boundary]");
const source=root.dataset.i18n||"../assets/epistemic-spiral/i18n.json";
const normalize=x=>String(x||"en").replace("-","_");
fetch(source,{cache:"no-store"}).then(r=>{if(!r.ok)throw new Error("i18n "+r.status);return r.json()}).then(data=>{
 const locales=data.locales||{};Object.keys(locales).forEach(k=>{const o=document.createElement("option");o.value=k;o.textContent=k;select.appendChild(o)});
 let preferred=normalize(document.documentElement.lang||navigator.language||"en");if(!locales[preferred])preferred=preferred.split("_")[0];if(!locales[preferred])preferred="en";select.value=preferred;
 const render=()=>{const v=locales[select.value]||locales.en;title.textContent=v.title;subtitle.textContent=v.subtitle;explanation.textContent=v.explanation;cosmos.textContent=v.cosmos;boundary.textContent=v.boundary;root.dir=select.value==="ar"?"rtl":"ltr";};
 select.addEventListener("change",render);render();
}).catch(e=>{boundary.textContent="HOLD: "+e.message});
})();
