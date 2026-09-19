// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. See LICENSE for component-specific terms.
// Read-only reader. Only explicit clicks copy/download text; no external submission.
(function () {
  'use strict';
  const names = {de:'Deutsch',en:'English',fr:'Français',es:'Español','pt-BR':'Português (Brasil)',it:'Italiano',tr:'Türkçe',ru:'Русский',ar:'العربية',hi:'हिन्दी',id:'Bahasa Indonesia',ja:'日本語',ko:'한국어','zh-CN':'简体中文'};
  // Labels: search, copy, download, all text, part, copied, copy manually, sources,
  // reading path, matches, source verification failed, source/evidence note.
  const labels = {
    de:['Im Artikel suchen','Für WhatsApp kopieren','Text herunterladen','Ganzer Artikel','Teil','Kopiert','Bitte den Text unten manuell kopieren.','Quellen und URLs','Lesepfad','Treffer','Quelldatei nicht verifiziert. Bitte die Markdown-Fassung öffnen.','Stand 19.09.2026. Quellenbindungen, keine neue Gesamtprüfung. Zenodo und Pages wurden hier nicht frisch öffentlich verifiziert.'],
    en:['Search this article','Copy for WhatsApp','Download text','Whole article','Part','Copied','Please copy the text below manually.','Sources and URLs','Reading path','Matches','Source file not verified. Please open the Markdown edition.','Snapshot 2026-09-19. Source bindings, not a new full-system test. Zenodo and Pages have no fresh public verification here.'],
    fr:['Rechercher dans l’article','Copier pour WhatsApp','Télécharger le texte','Article complet','Partie','Copié','Veuillez copier manuellement le texte ci-dessous.','Sources et URL','Parcours de lecture','Résultats','Source non vérifiée. Ouvrez la version Markdown.','État au 19.09.2026 : sources liées, non nouvel examen global. Zenodo et Pages ne sont pas fraîchement vérifiés ici.'],
    es:['Buscar en el artículo','Copiar para WhatsApp','Descargar texto','Artículo completo','Parte','Copiado','Copia manualmente el texto que aparece abajo.','Fuentes y URL','Ruta de lectura','Coincidencias','Fuente no verificada. Abre la versión Markdown.','Estado del 19.09.2026: fuentes vinculadas, no nueva prueba integral. Sin nueva verificación pública de Zenodo ni Pages.'],
    'pt-BR':['Buscar no artigo','Copiar para WhatsApp','Baixar texto','Artigo completo','Parte','Copiado','Copie manualmente o texto abaixo.','Fontes e URLs','Caminho de leitura','Resultados','Fonte não verificada. Abra a versão Markdown.','Estado de 19/09/2026: fontes vinculadas, não novo teste integral. Sem nova verificação pública de Zenodo ou Pages.'],
    it:['Cerca nell’articolo','Copia per WhatsApp','Scarica il testo','Articolo completo','Parte','Copiato','Copia manualmente il testo qui sotto.','Fonti e URL','Percorso di lettura','Risultati','Fonte non verificata. Apri la versione Markdown.','Stato al 19.09.2026: fonti collegate, non nuova verifica globale. Nessuna nuova verifica pubblica di Zenodo o Pages.'],
    tr:['Makalede ara','WhatsApp için kopyala','Metni indir','Makalenin tamamı','Bölüm','Kopyalandı','Lütfen aşağıdaki metni elle kopyalayın.','Kaynaklar ve URL’ler','Okuma yolu','Eşleşme','Kaynak doğrulanamadı. Markdown sürümünü açın.','19.09.2026 kaynak durumu; yeni bütün-sistem testi değil. Zenodo ve Pages için yeni kamuya açık doğrulama yok.'],
    ru:['Поиск в статье','Копировать для WhatsApp','Скачать текст','Вся статья','Часть','Скопировано','Скопируйте текст ниже вручную.','Источники и URL','Путь чтения','Совпадения','Источник не проверен. Откройте версию Markdown.','Срез на 19.09.2026: привязки источников, не новая общая проверка. Свежая публичная проверка Zenodo и Pages отсутствует.'],
    ar:['البحث في المقال','نسخ لواتساب','تنزيل النص','المقال كاملًا','جزء','تم النسخ','يرجى نسخ النص أدناه يدويًا.','المصادر والروابط','مسار القراءة','نتائج','لم يتم التحقق من المصدر. افتح نسخة Markdown.','حالة المصادر في 19 سبتمبر 2026، وليست فحصًا شاملًا جديدًا. لا يوجد تحقق عام جديد من Zenodo أو Pages هنا.'],
    hi:['लेख में खोजें','WhatsApp के लिए कॉपी करें','पाठ डाउनलोड करें','पूरा लेख','भाग','कॉपी किया','कृपया नीचे का पाठ स्वयं कॉपी करें।','स्रोत और URL','पढ़ने का मार्ग','मिलान','स्रोत सत्यापित नहीं हुआ। Markdown संस्करण खोलें।','19 सितंबर 2026 की स्रोत-स्थिति; नया पूर्ण परीक्षण नहीं। यहाँ Zenodo और Pages का ताज़ा सार्वजनिक सत्यापन नहीं है।'],
    id:['Cari dalam artikel','Salin untuk WhatsApp','Unduh teks','Seluruh artikel','Bagian','Disalin','Salin teks di bawah secara manual.','Sumber dan URL','Jalur membaca','Hasil','Sumber belum terverifikasi. Buka versi Markdown.','Sumber per 19 September 2026, bukan pengujian menyeluruh baru. Tanpa verifikasi publik baru Zenodo atau Pages.'],
    ja:['記事内を検索','WhatsApp用にコピー','テキストを保存','記事全体','部分','コピーしました','下のテキストを手動でコピーしてください。','出典とURL','読む道筋','一致','出典ファイルを確認できません。Markdown版を開いてください。','出典の基準日：2026年9月19日。新たな全体検証ではありません。ZenodoとPagesの公開状態は今回未確認です。'],
    ko:['글 안에서 검색','WhatsApp용 복사','텍스트 저장','글 전체','부분','복사됨','아래 텍스트를 직접 복사해 주세요.','출처와 URL','읽기 경로','검색 결과','출처 파일을 검증하지 못했습니다. Markdown판을 여세요.','2026년 9월 19일 출처 기준입니다. 새로운 전체 검증이 아니며 Zenodo와 Pages의 공개 상태는 새로 확인되지 않았습니다.'],
    'zh-CN':['在文章中搜索','复制到WhatsApp','下载文本','完整文章','部分','已复制','请手动复制下方文本。','来源与URL','阅读路径','匹配','源文件未通过验证，请打开Markdown版。','来源基准日为2026年9月19日，并非新的完整系统验证。本次未重新确认Zenodo与Pages的公开状态。']
  };
  const hosts = new Set(['github.com','goldkelch.github.io','doi.org','zenodo.org','datatracker.ietf.org']);
  function safeURL(raw) {
    const u = new URL(raw);
    if (u.protocol !== 'https:' || !hosts.has(u.hostname) || u.username || u.password || (u.port && u.port !== '443')) throw new Error('Unsafe source URL');
    return raw;
  }
  function chooseLocale(preferences) {
    for (const preference of preferences || []) {
      const value = String(preference).replace(/_/g,'-');
      const exact = Object.keys(names).find(k => k.toLowerCase() === value.toLowerCase());
      if (exact) return exact;
      if (/^zh(?:-Hans(?:-|$)|-CN$|-SG$|$)/i.test(value)) return 'zh-CN';
      if (/^zh/i.test(value)) continue; // Do not silently label Traditional Chinese as reviewed Simplified Chinese.
      const first = value.split('-')[0].toLowerCase();
      if (first === 'pt') return 'pt-BR';
      if (Object.hasOwn(names, first)) return first;
    }
    return 'en';
  }
  function parseDocument(markdown) {
    const refs = Object.create(null);
    for (const m of markdown.matchAll(/^\[([a-z]\d+)\]: (https:\/\/\S+)$/gm)) {
      if (refs[m[1]]) throw new Error('Duplicate reference');
      refs[m[1]] = safeURL(m[2]);
    }
    if (Object.keys(refs).length !== 39) throw new Error('Reference census mismatch');
    const sections = Object.create(null);
    const content = markdown.split('<!-- qikvrt-sources -->')[0];
    const markers = [...content.matchAll(/<!-- qikvrt-locale:([a-z]{2}(?:-[A-Z]{2})?) -->/g)];
    for (let i=0; i<markers.length; i++) {
      const marker=markers[i], code=marker[1];
      if (!Object.hasOwn(names,code) || sections[code]) throw new Error('Unexpected/duplicate locale');
      const block=content.slice(marker.index+marker[0].length, i+1<markers.length ? markers[i+1].index : content.length).replace(/<a id="[^"]+"><\/a>/,'').trim();
      const title=block.match(/^## ([^\n]+)\n/);
      if (!title) throw new Error('Missing title');
      const paragraphs=block.slice(title[0].length).trim().split(/\n\s*\n/);
      if (paragraphs.length!==13 || paragraphs.some(p => p.length<80)) throw new Error('Incomplete prose');
      const used=new Set();
      for (const p of paragraphs) for (const m of p.matchAll(/\[([^\]\n]+)\]\[([a-z]\d+)\]/g)) {
        if (!refs[m[2]]) throw new Error('Unbound reference');
        used.add(m[2]);
      }
      if (used.size!==39) throw new Error('Incomplete source coverage');
      sections[code]={title:title[1],paragraphs};
    }
    if (Object.keys(sections).length!==14) throw new Error('Incomplete language set');
    return {sections,refs};
  }
  function plainText(section, refs) {
    return section.title+'\n\n'+section.paragraphs.map(p => p.replace(/\[([^\]\n]+)\]\[([a-z]\d+)\]/g,(_,label,id)=>`${label} (${refs[id]})`)).join('\n\n');
  }
  function splitText(text,limit=3500) {
    if (!Number.isInteger(limit)||limit<100) throw new Error('Invalid chunk size');
    const result=[]; let current='';
    for (const paragraph of text.split(/\n\s*\n/)) {
      if (Array.from(current+(current?'\n\n':'')+paragraph).length<=limit) {current+=(current?'\n\n':'')+paragraph;continue;}
      if(current) {result.push(current.trim());current='';}
      if(Array.from(paragraph).length<=limit) {current=paragraph;continue;}
      for(const token of paragraph.split(/(\s+)/)) {
        if(Array.from(current+token).length>limit && current.trim()) {result.push(current.trim());current='';}
        const chars=Array.from(token);
        while(chars.length>limit) {result.push(chars.splice(0,limit).join(''));}
        current+=chars.join('');
      }
    }
    if(current.trim()) result.push(current.trim());
    return result;
  }
  if(typeof module!=='undefined' && module.exports) module.exports={names,labels,safeURL,chooseLocale,parseDocument,plainText,splitText};
  if(typeof document==='undefined') return;
  function appendMarked(parent,text,query) {
    if(!query) {parent.append(document.createTextNode(text));return 0;}
    const escaped=query.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
    const pattern=new RegExp(escaped,'giu');let pos=0,count=0;
    for(const match of text.matchAll(pattern)) {
      const next=match.index;
      parent.append(document.createTextNode(text.slice(pos,next)));
      const mark=document.createElement('mark');mark.textContent=match[0];parent.append(mark);
      pos=next+match[0].length;count++;
    }
    parent.append(document.createTextNode(text.slice(pos)));return count;
  }
  function appendParagraph(parent,text,refs,query) {
    const re=/\[([^\]\n]+)\]\[([a-z]\d+)\]/g;let offset=0,count=0;
    for(const m of text.matchAll(re)) {
      count+=appendMarked(parent,text.slice(offset,m.index),query);
      const a=document.createElement('a');a.href=refs[m[2]];a.rel='noopener noreferrer';a.dataset.sourceId=m[2];
      count+=appendMarked(a,m[1],query);parent.append(a);offset=m.index+m[0].length;
    }
    return count+appendMarked(parent,text.slice(offset),query);
  }
  async function start() {
    const get=id=>document.getElementById(id), lang=get('language');
    let locale=chooseLocale(navigator.languages||[navigator.language]), state, parts=[],full='';
    function hashState() {
      const raw=decodeURIComponent(location.hash.slice(1));
      const code=Object.keys(names).find(k=>raw===k||raw.startsWith(k+'-p'));
      return code?{code,anchor:raw}:null;
    }
    try {const selected=hashState();if(selected) locale=selected.code;} catch (_) { /* malformed user fragment: keep browser preference */ }
    function localize() {
      document.documentElement.lang=locale;document.documentElement.dir=locale==='ar'?'rtl':'ltr';
      const l=labels[locale];lang.value=locale;
      get('search-label').textContent=l[0];get('search').placeholder=l[0];get('copy').textContent=l[1];get('download').textContent=l[2];
      get('source-label').textContent=l[7];get('path-label').textContent=l[8];get('note').textContent=l[11];
      get('part-label').textContent=l[4];get('manual-label').textContent=l[6];get('full-source').textContent='Markdown · '+names[locale];
      get('full-source').href='WELCOME.md#'+locale;
    }
    localize();
    try {
      let text;
      const embedded=get('embedded-source');
      if(embedded) text=JSON.parse(embedded.textContent);
      else {
        const response=await fetch('WELCOME.md',{credentials:'omit',referrerPolicy:'no-referrer',cache:'no-store'});
        if(!response.ok) throw new Error('Source read failed');text=await response.text();
      }
      if(!globalThis.crypto?.subtle) throw new Error('Secure digest API unavailable');
      const bytes=new TextEncoder().encode(text);
      const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
      if(hash!==document.body.dataset.sourceSha256) throw new Error('Source digest mismatch');
      state=parseDocument(text);
    } catch(error) {
      get('status').textContent=labels[locale][10];get('status').setAttribute('role','alert');return;
    }
    get('controls').hidden=false;get('fallback').hidden=true;
    function render() {
      localize();const s=state.sections[locale],query=get('search').value.trim();
      get('title').textContent=s.title;document.title=s.title+' · Ingolf Lohmann';
      const article=get('article');article.replaceChildren();article.lang=locale;
      let count=0;const path=get('path');path.replaceChildren();
      s.paragraphs.forEach((text,i)=>{
        const p=document.createElement('p');p.id=locale+'-p'+String(i+1).padStart(2,'0');
        count+=appendParagraph(p,text,state.refs,query);article.append(p);
        const a=document.createElement('a');a.href='#'+p.id;a.textContent=String(i+1).padStart(2,'0')+' · '+p.textContent.slice(0,65)+'…';path.append(a);
      });
      get('matches').textContent=query?labels[locale][9]+': '+count:'';
      full=plainText(s,state.refs);parts=splitText(full);
      const part=get('part');part.replaceChildren();const whole=document.createElement('option');whole.value='all';whole.textContent=labels[locale][3];part.append(whole);
      parts.forEach((_,i)=>{const o=document.createElement('option');o.value=String(i);o.textContent=labels[locale][4]+' '+(i+1)+' / '+parts.length;part.append(o);});
      const sources=get('sources');sources.replaceChildren();
      for(const [id,url] of Object.entries(state.refs)) {
        const p=document.createElement('p'),a=document.createElement('a');a.href=url;a.rel='noopener noreferrer';a.textContent=id+' · '+url;a.dir='ltr';p.append(a);sources.append(p);
      }
      get('manual').hidden=true;get('status').textContent='';
    }
    function selectHash() {
      let h;try{h=hashState();}catch(_){return;}
      if(h && h.code!==locale) {locale=h.code;get('search').value='';render();}
      if(h) requestAnimationFrame(()=>get(h.anchor)?.scrollIntoView({block:'start'}));
    }
    function chosenText() {const value=get('part').value;return value==='all'?full:parts[Number(value)];}
    lang.addEventListener('change',()=>{locale=lang.value;get('search').value='';location.hash=locale;render();});
    addEventListener('hashchange',selectHash);
    get('search').addEventListener('input',render);
    get('copy').addEventListener('click',async()=>{
      const text=chosenText();
      try {if(!navigator.clipboard) throw new Error('Clipboard unavailable');await navigator.clipboard.writeText(text);get('status').textContent=labels[locale][5];}
      catch(_){get('manual-text').value=text;get('manual').hidden=false;get('manual-text').focus();get('manual-text').select();get('status').textContent=labels[locale][6];}
    });
    get('download').addEventListener('click',()=>{
      const part=get('part').value,suffix=part==='all'?'':'-'+String(Number(part)+1).padStart(2,'0');
      const url=URL.createObjectURL(new Blob([chosenText()+'\n'],{type:'text/plain;charset=utf-8'}));
      const a=document.createElement('a');a.href=url;a.download='QIKVRT-'+locale+suffix+'.txt';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
    });
    render();selectHash();
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',start,{once:true});else start();
}());
