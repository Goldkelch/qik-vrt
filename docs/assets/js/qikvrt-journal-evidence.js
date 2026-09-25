(async()=>{"use strict";
const root=document.querySelector("[data-qikvrt-claim-explorer]");
if(!root)return;
const src=root.getAttribute("data-claims-src")||"claims.json";
const esc=s=>String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\\":"&#39;",'"':"&quot;"}[c]||c));
try{
 const r=await fetch(src,{cache:"no-store"}); if(!r.ok) throw new Error("HTTP "+r.status);
 const data=await r.json(); const claims=data.claims||[];
 const kinds=[...new Set(claims.map(c=>c.kind))];
 root.innerHTML='<div class="claim-toolbar"><button data-kind="ALL" class="btn primary">Alle</button>'+kinds.map(k=>'<button data-kind="'+esc(k)+'" class="btn">'+esc(k)+'</button>').join("")+'</div><div class="claim-summary"></div><div class="claim-grid"></div>';
 const grid=root.querySelector(".claim-grid"), summary=root.querySelector(".claim-summary");
 const render=kind=>{
   const xs=kind==="ALL"?claims:claims.filter(c=>c.kind===kind);
   summary.textContent=xs.length+" von "+claims.length+" Aussagen";
   grid.innerHTML=xs.map(c=>'<article class="card claim-card"><div class="claim-meta"><span>'+esc(c.id)+'</span><span>'+esc(c.kind)+'</span><span>'+esc(c.status)+'</span></div><p><strong>'+esc(c.statement)+'</strong></p>'+(c.evidence?.length?'<div class="evidence-links">'+c.evidence.map((u,i)=>'<a href="'+esc(u)+'" rel="noopener">Beleg '+(i+1)+'</a>').join("")+'</div>':'<p class="mini">Einordnung/Meinung – kein externer Tatsachenbeleg beansprucht.</p>')+'</article>').join("");
 };
 root.addEventListener("click",e=>{const b=e.target.closest("button[data-kind]");if(!b)return;root.querySelectorAll("button[data-kind]").forEach(x=>x.classList.toggle("primary",x===b));render(b.dataset.kind);});
 render("ALL");
}catch(e){root.innerHTML='<p class="notice">Belegregister konnte nicht geladen werden. <a href="'+esc(src)+'">claims.json direkt öffnen</a>.</p>';}
})();