/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */

(function(){
  const root=document.documentElement;
  const themeButton=document.querySelector('#themeToggle');
  const copyButton=document.querySelector('#copyLink');
  const setTheme=theme=>{root.setAttribute('data-theme',theme);localStorage.setItem('qikvrt-theme',theme);};
  setTheme(localStorage.getItem('qikvrt-theme')||'dark');
  themeButton?.addEventListener('click',()=>setTheme(root.getAttribute('data-theme')==='dark'?'light':'dark'));
  copyButton?.addEventListener('click',async()=>{
    const stableUrl='https://goldkelch.github.io/qik-vrt/publications/';
    try{await navigator.clipboard.writeText(stableUrl);copyButton.textContent='URL kopiert';}
    catch(_error){copyButton.textContent=stableUrl;}
  });
})();
