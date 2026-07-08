
(function(){
  const KB_URL='assets/data/qikvrt_knowledge_base.json';
  let KB=null;
  async function loadKB(){ if(!KB){ KB=await fetch(KB_URL).then(r=>r.json()).catch(()=>null);} return KB; }
  function esc(s){return String(s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
  function classify(text){
    const t=(text||'').toLowerCase();
    const tags=[];
    if(/recht|ai act|pflicht|audit|nachweis|compliance|cra|nis2/.test(t)) tags.push('Rechts-/Nachweiskontext');
    if(/produkt|preis|kunde|verkauf|monetaris|pilot/.test(t)) tags.push('Produkt/Monetarisierung');
    if(/kognition|ontologie|unterschied|information|kausal|qik|vrt/.test(t)) tags.push('Künstliche Kognition');
    if(/node|seed|mesh|github|repository|workflow|registry/.test(t)) tags.push('Technische Architektur');
    if(!tags.length) tags.push('Allgemeine QIK-VRT-Einordnung');
    return tags;
  }
  function qikMap(text){
    const t=text.trim();
    return [
      'Q — Quantität: Welche Zustände, Risiken, Zählungen, Artefakte oder Nachweise sind betroffen?',
      'I — Information: Welche Unterschiede, Kontexte, Rollen, Quellen und Evidenzen müssen sichtbar werden?',
      'K — Kausalität: Welche Wirkung entsteht, wer trägt Verantwortung, und welcher nächste prüfbare Anschluss folgt?',
      'VRT — Realitätsprüfung: Welche Grenze verhindert Überbehauptung, blinde Automatisierung oder nicht belegte Freigabe?'
    ].join('\n');
  }
  function answerLocal(text,kb){
    const tags=classify(text);
    const lines=[];
    lines.push('QIK-VRT Kognitionskonsole — lokale Analyse');
    lines.push('');
    lines.push('Erkannter Fokus: '+tags.join(', '));
    lines.push('');
    lines.push(qikMap(text));
    lines.push('');
    if(tags.includes('Rechts-/Nachweiskontext')){
      lines.push('Einordnung: Für KI-, Software- und Lieferkettenprozesse wird nicht nur Funktion, sondern belegbare Verantwortbarkeit relevant: technische Dokumentation, Transparenz, Logging, Risk Control, Human Oversight, Cybersecurity und revisionsfähige Nachweise. QIK-VRT beantwortet diesen Bedarf mit run-id-spezifischen Evidence-Artefakten, Audit-Export, Dashboard und Release Freeze.');
      lines.push('Grenze: Das ist rechtlich anschlussfähige Evidenz, keine anwaltliche Einzelfallberatung und keine behördliche Zertifizierung.');
      lines.push('');
    }
    if(tags.includes('Technische Architektur')){
      lines.push('Architektur: Seed und Node interagieren autonom über öffentliche, autorisierte Repository-Artefakte. Der Seed akzeptiert Nodes, pflegt Index und Status, revalidiert bekannte oder queued Nodes und publiziert Audit/Dashboard. Nodes erneuern Registrierung, senden Health und bestätigen Seed-Acceptance.');
      lines.push('Schutzgrenzen: kein globales Scanning, keine Selbstverbreitung, keine fremde Repository-Mutation, keine Remote-Wirkung ohne Autorisierung.');
      lines.push('');
    }
    if(tags.includes('Künstliche Kognition')){
      lines.push('Kognitionslesart: QIK-VRT behandelt Kognition als geordnete Verarbeitung von Unterschieden mit Wirkung und Verantwortungsgrenze. Der initiale Unterschied ist der kleinste anschlussfähige Ausgangspunkt: Ohne Unterschied keine Information, ohne Information keine gerichtete Wirkung, ohne Wirkung keine verantwortbare Prüfung.');
      lines.push('');
    }
    if(tags.includes('Produkt/Monetarisierung')){
      lines.push('Produktnutzen: QIK-VRT Trust Mesh verkauft nicht nur Automatisierung, sondern prüfbare Vertrauenszustände: Repository-native Evidence, Auditfähigkeit, Provenienz, Governance, Pilotfähigkeit und Compliance-Readiness.');
      lines.push('');
    }
    lines.push('Nächster sinnvoller Anschluss: Formuliere den konkreten Fall als Repository, Artefakt, Risiko, gewünschte Entscheidung und benötigten Nachweis. Die Konsole kann daraus eine QIK/VRT-Prüfstruktur ableiten.');
    lines.push('');
    lines.push('Basis: '+(kb&&kb.product?kb.product:'QIK-VRT Trust Mesh')+' | Referenzlauf '+(kb&&kb.reference_run?kb.reference_run:'4AV1_20260708T174034Z_709544'));
    return lines.join('\n');
  }
  window.QIKVRTLocalEngine={loadKB, answerLocal, classify};
})();
