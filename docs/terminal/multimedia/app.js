// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
'use strict';
const el=id=>document.getElementById(id);
let status=null,selected=null,objectUrl=null,video=null,images=[],result=null,busy=false,selection=0;
let turns=[],microphone=null,camera=null,recorder=null,recordingTimer=null,recordingPending=false,cameraPending=false,captureEpoch=0;
function activity(text){el('activity').textContent=text;}
function buttons(){
 const recording=!!recorder||recordingPending;
 el('generate').disabled=busy||recording||!status?.ready||(el('repository').checked&&!status?.repository_ready);
 el('transcribe').disabled=busy||recording||!status?.audio_ready||!selected||selected.type.startsWith('image/');
 for(const id of ['file','clear','newChat','repository'])el(id).disabled=busy||recording;
 el('microphone').disabled=busy||recording;el('stopRecording').disabled=!recorder;
 el('camera').disabled=busy||!!camera||cameraPending;el('stopCamera').disabled=!camera;
}
async function refresh(){
 try{const response=await fetch('/api/multimedia/status',{cache:'no-store'});if(!response.ok)throw Error('Lokaler Zugang erforderlich');status=await response.json();
 el('runtime').textContent=status.ready?status.model+' ist verbunden.':'Das lokale Modell ist noch nicht gestartet.';
 if(!status.audio_ready)el('runtime').textContent+=' Offline-Spracherkennung ist noch nicht installiert.';
 el('repositoryStatus').textContent=status.repository_ready?'Repository-Inventar verfügbar. Relevante Auszüge werden mit ihrer Herkunft an das Modell übergeben.':'Repository-Inventar fehlt oder ist beschädigt. Quellensuche derzeit nicht verfügbar.';
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
function stopCamera(){
 if(camera)camera.getTracks().forEach(track=>track.stop());camera=null;
 if(video?.srcObject){video.srcObject=null;video=null;el('preview').replaceChildren();el('capture').hidden=true;}
 el('captureStatus').textContent=recorder?'Mikrofon nimmt auf.':'Mikrofon und Kamera sind aus.';buttons();
}
function stopRecording(){if(recorder&&recorder.state!=='inactive')recorder.stop();if(microphone)microphone.getTracks().forEach(track=>track.stop());microphone=null;clearTimeout(recordingTimer);}
function clear(){captureEpoch++;selection++;stopCamera();selected=null;video=null;images=[];if(objectUrl)URL.revokeObjectURL(objectUrl);objectUrl=null;el('preview').replaceChildren();el('file').value='';el('capture').hidden=true;el('fileInfo').textContent='Die Auswahl bleibt zunächst im Browser.';drawImages();buttons();}
function selectFile(file){
 stopCamera();if(objectUrl)URL.revokeObjectURL(objectUrl);const current=++selection;selected=file;video=null;el('preview').replaceChildren();el('capture').hidden=true;
 objectUrl=URL.createObjectURL(file);el('fileInfo').textContent=file.name+' · '+(file.size/1024/1024).toFixed(1)+' MiB';
 let media;
 if(file.type.startsWith('image/')){media=document.createElement('img');media.alt=file.name;media.onload=()=>{if(current!==selection)return;try{addImage(media,file.name);}catch(error){activity(error.message);}};}
 else if(file.type.startsWith('video/')||/\.mov$/i.test(file.name)){media=document.createElement('video');media.controls=true;media.preload='metadata';video=media;el('capture').hidden=false;}
 else{media=document.createElement('audio');media.controls=true;media.preload='metadata';}
 media.onerror=()=>{if(current===selection)activity('Dieses Dateiformat kann nicht wiedergegeben werden. Bitte ein unterstütztes Format wie WebM verwenden.');};media.src=objectUrl;el('preview').append(media);buttons();
}
el('file').onchange=()=>{const file=el('file').files[0];if(!file)return;if(file.size>256*1024*1024){activity('Die Vorschau unterstützt Dateien bis 256 MiB.');el('file').value='';return;}captureEpoch++;selectFile(file);};
el('capture').onclick=()=>{try{if(!video)throw Error('Kein Video ausgewählt.');addImage(video,(camera?'Kamera':selected.name)+' @ '+video.currentTime.toFixed(3)+' s');activity('Dieses Videobild wurde zur Modellauswahl hinzugefügt.');}catch(error){activity(error.message);}};
el('microphone').onclick=async()=>{
 if(!navigator.mediaDevices?.getUserMedia||!window.MediaRecorder){activity('Dieser Browser bietet hier keine Mikrofonaufnahme. Audiodateien können weiterhin gewählt werden.');return;}
 recordingPending=true;buttons();const epoch=captureEpoch;
 try{
 const stream=await navigator.mediaDevices.getUserMedia({audio:true});
 if(epoch!==captureEpoch){stream.getTracks().forEach(t=>t.stop());return;}
 microphone=stream;const mime=['audio/webm;codecs=opus','audio/ogg;codecs=opus'].find(x=>MediaRecorder.isTypeSupported(x));
 recorder=mime?new MediaRecorder(stream,{mimeType:mime}):new MediaRecorder(stream);
 const active=recorder,chunks=[];let bytes=0,failed=false;
 active.ondataavailable=event=>{bytes+=event.data.size;if(bytes>12*1024*1024){failed=true;stopRecording();activity('Aufnahme überschreitet 12 MiB. Bitte kürzer aufnehmen.');}else if(event.data.size)chunks.push(event.data);};
 active.onerror=()=>{failed=true;stopRecording();activity('Mikrofonaufnahme fehlgeschlagen.');};
 active.onstop=()=>{
 clearTimeout(recordingTimer);stream.getTracks().forEach(t=>t.stop());microphone=null;recorder=null;
 if(!failed&&bytes&&epoch===captureEpoch){const type=active.mimeType||'audio/webm';selectFile(new File(chunks,'mikrofon.'+(type.includes('ogg')?'ogg':'webm'),{type}));activity('Aufnahme bereit. Lokal transkribieren und das Transkript prüfen.');}
 el('captureStatus').textContent=camera?'Kamera ist aktiv.':'Mikrofon und Kamera sind aus.';buttons();
 };
 active.start(1000);recordingTimer=setTimeout(stopRecording,115000);el('captureStatus').textContent='Mikrofon nimmt auf · automatisches Ende nach 115 Sekunden.';
 }catch(error){if(microphone)microphone.getTracks().forEach(t=>t.stop());microphone=null;recorder=null;activity('Mikrofon nicht verfügbar: '+error.message);}
 finally{recordingPending=false;buttons();}
};
el('stopRecording').onclick=stopRecording;
el('camera').onclick=async()=>{
 if(!navigator.mediaDevices?.getUserMedia){activity('Kamera hier nicht verfügbar. Bitte ein Video auswählen.');return;}
 cameraPending=true;buttons();const epoch=captureEpoch;
 try{const stream=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:768},height:{ideal:576}},audio:false});
 if(epoch!==captureEpoch){stream.getTracks().forEach(t=>t.stop());return;}
 stopCamera();camera=stream;video=document.createElement('video');video.muted=true;video.autoplay=true;video.playsInline=true;video.srcObject=stream;el('preview').replaceChildren(video);await video.play();el('capture').hidden=false;el('captureStatus').textContent='Kamera ist aktiv. Nur ausdrücklich hinzugefügte Bilder gehen an das Modell.';
 }catch(error){stopCamera();activity('Kamera nicht verfügbar: '+error.message);}finally{cameraPending=false;buttons();}
};
el('stopCamera').onclick=stopCamera;
async function post(path,body){
 const response=await fetch('/api/multimedia/'+path,{method:'POST',headers:{'Content-Type':'application/json','X-QIKVRT-Media-Token':status.csrf},body:JSON.stringify(body)});
 const value=await response.json();if(!response.ok)throw Error(value.reason||'Verarbeitung fehlgeschlagen');return value;
}
function history(){
 let pairs=turns.slice(-3).map(t=>[{role:'user',content:t.prompt.slice(0,1800)},{role:'assistant',content:t.result.text.slice(0,1800)}]);
 while(pairs.flat().reduce((n,m)=>n+m.content.length,0)>4000)pairs.shift();return pairs.flat();
}
function drawSources(context){
 el('sources').replaceChildren();el('sourceDetails').open=!!context;
 el('sourceStatus').textContent=context?(context.sources.length+' Auszüge aus '+context.scanned_files+' gelesenen Dateien. Begrenzte lokale Suche; kein vollständiger Mesh-Abgleich. Quellen belegen ihre eigenen Aussagen, nicht automatisch die Modellantwort.'):'Repository-Quellensuche war ausgeschaltet.';
 for(const source of context?.sources||[]){const detail=document.createElement('details'),title=document.createElement('summary'),identity=document.createElement('p'),excerpt=document.createElement('pre');title.textContent='['+source.id+'] '+source.path+' · ab Zeile '+source.line_start;identity.textContent='SHA-256: '+source.sha256;excerpt.textContent=source.excerpt;detail.append(title,identity,excerpt);el('sources').append(detail);}
}
function drawConversation(){el('conversation').replaceChildren();for(const turn of turns){const block=document.createElement('article'),question=document.createElement('p'),answer=document.createElement('pre');question.textContent='Sie: '+turn.prompt;answer.textContent=turn.result.text;block.append(question,answer);el('conversation').append(block);}}
el('generate').onclick=async()=>{
 const prompt=el('prompt').value.trim();if(!prompt){activity('Bitte eine Frage eingeben.');return;}
 const body={prompt,images:images.map(x=>({...x})),history:history(),repository:el('repository').checked};
 busy=true;buttons();activity('Repository-Auszüge und Eingaben werden lokal verarbeitet …');
 try{result=await post('generate',body);el('answer').textContent=result.text;el('receipt').textContent=JSON.stringify(result,null,2);turns.push({prompt,result});turns=turns.slice(-20);drawConversation();drawSources(result.repository_context);el('download').disabled=false;el('speak').disabled=!('speechSynthesis' in window);activity(result.finish_reason==='length'?'Antwort erreicht die Token-Grenze und kann unvollständig sein.':'Antwort ist bereit. Bitte an den Quellen prüfen.');}
 catch(error){activity('Verarbeitung angehalten: '+error.message);}finally{busy=false;buttons();}
};
function fileBase64(file){return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onerror=()=>reject(Error('Datei nicht lesbar'));reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.readAsDataURL(file);});}
el('transcribe').onclick=async()=>{
 const file=selected;if(!file||file.size>12*1024*1024){activity('Für die Spracherkennung bitte einen Ausschnitt bis 12 MiB verwenden.');return;}
 busy=true;buttons();activity('Audio wird auf dem Terminal-Rechner transkribiert …');
 try{const value=await post('transcribe',{data:await fileBase64(file),language:el('language').value});el('transcript').value=value.text;el('receipt').textContent=JSON.stringify(value,null,2);activity(value.state==='NO_AUDIO_ENERGY'?'Die Datei enthält digitale Stille. Kein Transkript erzeugt.':'Transkript ist bereit. Prüfen Sie es vor der Übernahme.');}
 catch(error){activity('Transkription angehalten: '+error.message);}finally{busy=false;buttons();}
};
el('useTranscript').onclick=()=>{const value=el('transcript').value.trim();if(!value){activity('Kein Transkript vorhanden.');return;}const text=el('prompt').value+'\n\nVom Nutzer geprüftes Transkript:\n'+value;if(text.length>12000){activity('Frage und Transkript überschreiten 12.000 Zeichen. Bitte kürzen.');return;}el('prompt').value=text;activity('Transkript in die nächste Frage übernommen.');};
el('speak').onclick=()=>{if(result&&'speechSynthesis'in window){const voice=speechSynthesis.getVoices().find(v=>v.localService&&v.lang.startsWith(el('language').value));if(!voice){activity('Keine passende lokale Stimme verfügbar.');return;}speechSynthesis.cancel();const speech=new SpeechSynthesisUtterance(result.text);speech.voice=voice;speech.lang=voice.lang;speechSynthesis.speak(speech);}};
el('stopSpeech').onclick=()=>{if('speechSynthesis'in window)speechSynthesis.cancel();};
el('download').onclick=()=>{if(!result)return;const receipt={schema:'qikvrt_local_conversation_v1',turns,effect_ack_done:false};const url=URL.createObjectURL(new Blob([JSON.stringify(receipt,null,2)],{type:'application/json'})),link=document.createElement('a');link.href=url;link.download='qikvrt-gespraech.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
el('newChat').onclick=()=>{clear();turns=[];result=null;el('prompt').value='';el('transcript').value='';el('answer').textContent='Noch keine Antwort.';el('receipt').textContent='Noch kein Verarbeitungsbeleg.';el('download').disabled=true;el('speak').disabled=true;drawConversation();drawSources(null);if('speechSynthesis'in window)speechSynthesis.cancel();activity('Neues Gespräch begonnen.');};
el('repository').onchange=buttons;el('clear').onclick=clear;el('refresh').onclick=refresh;
window.addEventListener('pagehide',()=>{captureEpoch++;stopRecording();stopCamera();if(objectUrl)URL.revokeObjectURL(objectUrl);if('speechSynthesis'in window)speechSynthesis.cancel();});refresh();
