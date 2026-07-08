
(function(){
  const $=sel=>document.querySelector(sel);
  const $$=sel=>Array.from(document.querySelectorAll(sel));
  function setTheme(t){document.documentElement.setAttribute('data-theme',t);localStorage.setItem('qikvrt-theme',t)}
  function initTheme(){setTheme(localStorage.getItem('qikvrt-theme')||'dark'); $('#themeToggle')?.addEventListener('click',()=>setTheme(document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark'));}
  async function initTimeline(){
    const el=$('#timelineData'); if(!el) return;
    const data=await fetch('assets/data/qikvrt_timeline.json').then(r=>r.json()).catch(()=>[]);
    el.innerHTML=data.map(x=>`<div class="tl"><p class="mini">${x.phase}</p><h3>${x.title}</h3><ul>${x.items.map(i=>`<li>${i}</li>`).join('')}</ul></div>`).join('');
  }
  function copyLink(){navigator.clipboard&&navigator.clipboard.writeText(location.href).then(()=>{const b=$('#copyLink'); if(b)b.textContent='Link kopiert';});}
  async function initConsole(){
    const ask=$('#askBtn'), out=$('#consoleOutput'); if(!ask||!out) return;
    const kb=await window.QIKVRTLocalEngine.loadKB();
    ask.addEventListener('click',async()=>{
      const prompt=$('#promptInput').value.trim();
      if(!prompt){out.textContent='Bitte eine Frage oder einen Fall eingeben.';return;}
      const mode=$('#modeSelect').value;
      out.textContent='Arbeite...';
      try{
        if(mode==='github'){
          const token=$('#ghToken').value.trim();
          if(!token){out.textContent='GitHub Models Modus benötigt einen eigenen Token mit models:read. Für öffentliche No-Token-Nutzung ist die nächste Ausbaustufe eine GitHub App oder ein Server-Proxy.';return;}
          const model=$('#modelInput').value.trim()||'openai/gpt-4o-mini';
          out.textContent=await window.QIKVRTGitHubModels.askGitHubModels(prompt,token,model);
        }else{
          out.textContent=window.QIKVRTLocalEngine.answerLocal(prompt,kb);
        }
      }catch(e){out.textContent=String(e.message||e);}
    });
    $$('#examplePrompts button').forEach(b=>b.addEventListener('click',()=>{$('#promptInput').value=b.dataset.prompt; ask.click();}));
    $('#modeSelect')?.addEventListener('change',e=>{$('#githubFields').hidden=e.target.value!=='github';});
  }
  document.addEventListener('DOMContentLoaded',()=>{initTheme();initTimeline();initConsole();$('#copyLink')?.addEventListener('click',copyLink)});
})();
