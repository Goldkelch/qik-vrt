// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
'use strict';
const el=id=>document.getElementById(id);
let status=null, selected=null, objectUrl=null, video=null, images=[], result=null, busy=false, selection=0;
function activity(text){el('activity').textContent=text;}
function buttons(){el('generate').disabled=busy||!status?.ready;el('transcribe').disabled=busy||!status?.audio_ready||!selected||selected.type.startsWith('image/');}
async function refresh(){
 try{const response=await fetch('/api/multimedia/status',{cache:'no-store'});if(!response.ok)throw Error('Lokaler Zugang erforderlich');status=await response.json();
 el('runtime').textContent=status.ready?'SmolVLM2 ist verbunden.':'Das lokale Modell ist noch nicht gestartet.';
 if(!status.audio_ready)el('runtime').textContent+=' Offline-Spracherkennung ist noch nicht installiert.';
 }catch(error){status=null;el('runtime').textContent='Verbindung nicht verfügbar: '+error.message;}
 buttons();
}
function drawImages(){
 el('images').replaceChildren();
 for(const entry of images){const figure=document.createElement('figure'),img=document.createElement('img'),caption=document.createElement('figcaption');img.src=entry.data;img.alt=entry.label;caption.textContent=entry.label;figure.append(img,caption);el('images').append(figure);}
}
function addImage(source,label){
 if(images.length>=4)throw Error('Es können höchstens vier Bilder übergeben werden.');
 const width=source.videoWidth||source.naturalWidth,height=source.videoHeight||source.naturalHeight;
 if(!width||!height)throw Error('Bild ist noch nicht verfügbar.');
 const scale=Math.min(1,768/Math.max(width,height)),canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(width*scale));canvas.height=Math.max(1,Math.round(height*scale));
 canvas.getContext('2d').drawImage(source,0,0,canvas.width,canvas.height);
 images.push({data:canvas.toDataURL('image/jpeg',.85),label:label.slice(0,160)});drawImages();
}
function clear(){selection++;selected=null;video=null;images=[];if(objectUrl)URL.revokeObjectURL(objectUrl);objectUrl=null;el('preview').replaceChildren();el('file').value='';el('capture').hidden=true;el('fileInfo').textContent='Die Auswahl bleibt zunächst im Browser.';drawImages();buttons();}
el('file').onchange=()=>{
 const file=el('file').files[0];if(!file)return;
 if(file.size>256*1024*1024){activity('Die Vorschau unterstützt Dateien bis 256 MiB.');el('file').value='';return;}
 if(objectUrl)URL.revokeObjectURL(objectUrl);const current=++selection;selected=file;video=null;el('preview').replaceChildren();el('capture').hidden=true;
 objectUrl=URL.createObjectURL(file);el('fileInfo').textContent=file.name+' · '+(file.size/1024/1024).toFixed(1)+' MiB';
 let media;
 if(file.type.startsWith('image/')){media=document.createElement('img');media.alt=file.name;media.onload=()=>{if(current!==selection)return;try{addImage(media,file.name);}catch(error){activity(error.message);}};}
 else if(file.type.startsWith('video/')||/\.mov$/i.test(file.name)){media=document.createElement('video');media.controls=true;media.preload='metadata';video=media;el('capture').hidden=false;}
 else{media=document.createElement('audio');media.controls=true;media.preload='metadata';}
 media.onerror=()=>{if(current===selection)activity('Firefox kann dieses Dateiformat nicht wiedergeben. Bitte ein unterstütztes Format wie WebM verwenden.');};media.src=objectUrl;el('preview').append(media);buttons();
};
el('capture').onclick=()=>{try{if(!video)throw Error('Kein Video ausgewählt.');addImage(video,selected.name+' @ '+video.currentTime.toFixed(3)+' s');activity('Dieses Videobild wurde zur Modellauswahl hinzugefügt.');}catch(error){activity(error.message);}};
async function post(path,body){
 const response=await fetch('/api/multimedia/'+path,{method:'POST',headers:{'Content-Type':'application/json','X-QIKVRT-Media-Token':status.csrf},body:JSON.stringify(body)});
 const value=await response.json();if(!response.ok)throw Error(value.reason||'Verarbeitung fehlgeschlagen');return value;
}
el('generate').onclick=async()=>{
 const prompt=el('prompt').value.trim();if(!prompt){activity('Bitte eine Frage eingeben.');return;}
 busy=true;buttons();activity('Das lokale Modell verarbeitet die ausgewählten Eingaben …');
 try{result=await post('generate',{prompt,images:images.map(x=>({...x}))});el('answer').textContent=result.text;el('receipt').textContent=JSON.stringify(result,null,2);el('download').disabled=false;el('speak').disabled=!('speechSynthesis' in window);activity(result.finish_reason==='length'?'Antwort erreicht die Token-Grenze und kann unvollständig sein.':'Antwort ist bereit. Bitte inhaltlich prüfen.');}
 catch(error){activity('Verarbeitung angehalten: '+error.message);}finally{busy=false;buttons();}
};
function fileBase64(file){return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onerror=()=>reject(Error('Datei nicht lesbar'));reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.readAsDataURL(file);});}
el('transcribe').onclick=async()=>{
 if(!selected||selected.size>12*1024*1024){activity('Für die Spracherkennung bitte einen Ausschnitt bis 12 MiB verwenden.');return;}
 busy=true;buttons();activity('Audio wird auf dem Terminal-Rechner transkribiert …');
 try{const value=await post('transcribe',{data:await fileBase64(selected),language:el('language').value});el('transcript').value=value.text;el('receipt').textContent=JSON.stringify(value,null,2);activity(value.state==='NO_AUDIO_ENERGY'?'Die Datei enthält digitale Stille. Kein Transkript erzeugt.':'Transkript ist bereit. Prüfen Sie es vor der Übernahme.');}
 catch(error){activity('Transkription angehalten: '+error.message);}finally{busy=false;buttons();}
};
el('useTranscript').onclick=()=>{const value=el('transcript').value.trim();if(!value){activity('Kein Transkript vorhanden.');return;}const text=el('prompt').value+'\n\nVom Nutzer geprüftes Transkript:\n'+value;if(text.length>12000){activity('Frage und Transkript überschreiten 12.000 Zeichen. Bitte kürzen.');return;}el('prompt').value=text;activity('Transkript in die nächste Frage übernommen.');};
el('speak').onclick=()=>{if(result&&'speechSynthesis'in window){if(!speechSynthesis.getVoices().length){activity('In diesem Browser ist keine Stimme zum Vorlesen verfügbar.');return;}speechSynthesis.cancel();speechSynthesis.speak(new SpeechSynthesisUtterance(result.text));}};
el('stopSpeech').onclick=()=>{if('speechSynthesis'in window)speechSynthesis.cancel();};
el('download').onclick=()=>{if(!result)return;const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'})),link=document.createElement('a');link.href=url;link.download='qikvrt-modellantwort.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
el('clear').onclick=clear;el('refresh').onclick=refresh;refresh();
