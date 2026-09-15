(() => {
  if (document.getElementById("qikvrt-ai-terminal-host")) return;

  const host = document.createElement("section");
  host.id = "qikvrt-ai-terminal-host";
  host.setAttribute("aria-label", "QIKVRT AI Terminal");
  host.innerHTML = `
    <header class="qv-head">
      <div><strong>QIKVRT · AI TERMINAL</strong><small> source-bound · EFFECT_ACK gated</small></div>
      <div class="qv-head-actions"><button data-act="observe">↻ Observe</button><button data-act="options" aria-label="Personalize">⚙</button><button data-act="collapse" aria-label="Collapse">—</button></div>
    </header>
    <div class="qv-body">
      <div class="qv-status" data-role="status">OBSERVE</div>
      <pre class="qv-output" data-role="output" aria-live="polite">Terminal initialized. No effect authorized.</pre>
      <label class="qv-label" for="qv-command">Input</label>
      <textarea id="qv-command" data-role="command" rows="3" placeholder="Text input to the repository-side terminal counterpart"></textarea>
      <div class="qv-media-row">
        <button data-act="audio">🎙 Start audio</button>
        <button data-act="camera">📷 Start camera</button>
        <button data-act="snapshot" disabled>◉ Snapshot</button>
        <span data-role="media-state">media local</span>
      </div>
      <video data-role="video" playsinline muted hidden></video>
      <div class="qv-effect-row">
        <button class="qv-prepare" data-act="prepare">Prepare</button>
        <button class="qv-commit" data-act="commit" disabled>Commit</button>
        <span>Prepare ≠ effect · Commit requires DONE</span>
      </div>
    </div>`;
  document.body.appendChild(host);

  const $ = selector => host.querySelector(selector);
  const output = $("[data-role=output]");
  const status = $("[data-role=status]");
  const command = $("[data-role=command]");
  const video = $("[data-role=video]");
  const mediaState = $("[data-role=media-state]");
  const commitButton = $("[data-act=commit]");
  const snapshotButton = $("[data-act=snapshot]");

  // Read-only monitor projection. Stream receipt delivery never calls Prepare,
  // Commit or OBSERVE_AUTHORITY and never replaces the protected input buffer.
  const monitor = document.createElement("section");
  monitor.setAttribute("aria-label", "Repository Live-Monitor");
  monitor.className = "qv-live-monitor";
  const liveTitle = document.createElement("h3");
  liveTitle.textContent = "Repository · Live-Monitor";
  const liveState = document.createElement("p");
  liveState.setAttribute("data-role", "live-state");
  liveState.setAttribute("role", "status");
  const liveJournal = document.createElement("ol");
  liveJournal.setAttribute("data-role", "live-events");
  liveJournal.setAttribute("role", "log");
  liveJournal.setAttribute("aria-live", "polite");
  liveJournal.setAttribute("aria-relevant", "additions");
  const liveNote = document.createElement("small");
  liveNote.textContent = "Letzte 256 Belege · Empfangsreihenfolge, nicht Zeit als Kausalbeweis. Anzeige erteilt keine Freigabe.";
  monitor.append(liveTitle, liveState, liveJournal, liveNote);
  output.parentNode.insertBefore(monitor, output);
  const liveStyle = document.createElement("style");
  liveStyle.textContent = `
    #qikvrt-ai-terminal-host .qv-live-monitor {font-family:system-ui,sans-serif;margin:0 0 14px}
    #qikvrt-ai-terminal-host .qv-live-monitor h3 {margin:0 0 6px;font-size:1.1em;color:var(--qv-accent)}
    #qikvrt-ai-terminal-host [data-role=live-state] {font-size:.9em;margin:0 0 12px;color:#d0bf8c}
    #qikvrt-ai-terminal-host [data-role=live-state][data-state=CONNECTED],
    #qikvrt-ai-terminal-host [data-role=live-state][data-state=EVENT] {color:#b7e39a}
    #qikvrt-ai-terminal-host [data-role=live-state][data-state=HOLD] {color:#ffb1a8}
    #qikvrt-ai-terminal-host [data-role=live-events] {margin:0 0 8px;padding:0;list-style:none;max-height:340px;overflow:auto}
    #qikvrt-ai-terminal-host [data-role=live-events] li {margin:0 0 8px;padding:12px;border:1px solid #324b61;border-left:3px solid var(--qv-accent);border-radius:8px;background:#061727}
    #qikvrt-ai-terminal-host [data-role=live-events] li[data-result=success] {border-left-color:#91ce89}
    #qikvrt-ai-terminal-host [data-role=live-events] li[data-result=failure] {border-left-color:#ef8b82}
    #qikvrt-ai-terminal-host [data-role=live-events] p {margin:5px 0;font-size:.87em;color:#c8d4df;overflow-wrap:anywhere}
    #qikvrt-ai-terminal-host [data-role=live-events] summary {cursor:pointer;font-size:.85em;color:var(--qv-accent)}
    #qikvrt-ai-terminal-host [data-role=live-events] pre {white-space:pre-wrap;word-break:break-all;font-size:11px}
    #qikvrt-ai-terminal-host .qv-live-monitor small {display:block;opacity:.7;font-size:.78em}
  `;
  host.appendChild(liveStyle);
  const displayed = new Map();
  let liveRevision = 0;

  function showLiveState(name, detail) {
    const labels = {
      CONNECTED: "Verbunden · Verbindung offen; kein Fortschritt ohne neuen Beleg.",
      EVENT: "Beleg empfangen · Folgeereignisse erscheinen automatisch.",
      RECONNECTING: "Verbindung unterbrochen · letzte Belege bleiben sichtbar, sind aber nicht frisch.",
      HOLD: "Monitor angehalten · gebundene Fortsetzung erforderlich."
    };
    liveState.dataset.state = name || "UNBOUND";
    liveState.textContent = labels[name] || "Noch kein gebundener Monitorstrom empfangen.";
    if (typeof detail === "string" && detail) liveState.textContent += " " + detail;
  }

  function appendLiveReceipts(records) {
    if (!Array.isArray(records)) { showLiveState("HOLD", "Ungültiges lokales Journal."); return; }
    for (const receipt of records) {
      if (!receipt || receipt.schema !== "qikvrt_live_event_v1" || receipt.repository !== "Goldkelch/qik-vrt" ||
          typeof receipt.event_id !== "string" || !receipt.subject || !/^[0-9a-f]{40}$/.test(receipt.subject.head_sha || "")) {
        showLiveState("HOLD", "Ereignis ohne gültige Quellbindung."); return;
      }
      if (displayed.has(receipt.event_id)) continue;
      const item = document.createElement("li");
      item.setAttribute("data-event-id", receipt.event_id);
      const payload = receipt.payload || {};
      const result = typeof payload.conclusion === "string" ? payload.conclusion : "";
      item.dataset.result = result;
      const title = document.createElement("strong");
      const verbs = {OBSERVE: "Beobachtung", CLASSIFY: "Einordnung", ACTION: "Aktion gemeldet", EFFECT: "Wirkung gemeldet", READBACK: "Rücklesung", SUCCESSOR: "Nachfolger gemeldet", HOLD: "Blockierung"};
      const sign = result === "success" ? "✓ " : result === "failure" ? "✗ " : "→ ";
      title.textContent = sign + (verbs[receipt.verb] || receipt.verb || "Ereignis") + (typeof payload.workflow_name === "string" ? " · " + payload.workflow_name : "");
      const binding = document.createElement("p");
      binding.textContent = receipt.repository + " · " + receipt.subject.head_sha.slice(0, 12) + " · " + (receipt.phase || "Phase offen") + " · " + (receipt.causal_state || "Zustand offen");
      const details = document.createElement("details");
      const summary = document.createElement("summary");
      summary.textContent = "Quellbeleg · " + receipt.event_id;
      const raw = document.createElement("pre");
      // All external values are text, never HTML or executable event handlers.
      raw.textContent = JSON.stringify(receipt, null, 2);
      details.append(summary, raw);
      item.append(title, binding, details);
      liveJournal.appendChild(item);
      displayed.set(receipt.event_id, item);
      if (displayed.size > 256) {
        const oldest = displayed.keys().next().value;
        liveJournal.removeChild(displayed.get(oldest));
        displayed.delete(oldest);
      }
    }
  }

  showLiveState("UNBOUND");
  browser.storage.onChanged.addListener((changes, area) => {
    if (area !== "local") return;
    if (!changes.qikvrtLiveEvents && !changes.qikvrtLiveEventState && !changes.qikvrtLiveEventError) return;
    liveRevision += 1;
    if (changes.qikvrtLiveEventState) showLiveState(changes.qikvrtLiveEventState.newValue, changes.qikvrtLiveEventError && changes.qikvrtLiveEventError.newValue);
    if (changes.qikvrtLiveEvents) appendLiveReceipts(changes.qikvrtLiveEvents.newValue);
  });
  const startupRevision = liveRevision;
  browser.storage.local.get(["qikvrtLiveEvents", "qikvrtLiveEventState", "qikvrtLiveEventError"]).then(stored => {
    // Do not replay an older startup snapshot after a newer pushed window.
    if (liveRevision !== startupRevision) return;
    showLiveState(stored.qikvrtLiveEventState, stored.qikvrtLiveEventError);
    appendLiveReceipts(stored.qikvrtLiveEvents || []);
  }).catch(error => showLiveState("HOLD", error.message));

  let audioStream = null;
  let audioRecorder = null;
  let audioChunks = [];
  let audioBlob = null;
  let videoStream = null;
  let snapshotBlob = null;
  let prepared = null;
  let preparedRequest = null;

  function render(value) {
    output.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  }

  function setState(name, detail = "") {
    status.textContent = detail ? `${name} · ${detail}` : name;
    status.dataset.state = name;
  }

  async function applyPreferences() {
    const stored = await browser.storage.local.get("qikvrtTerminalPreferences");
    const p = stored.qikvrtTerminalPreferences || {};
    host.style.setProperty("--qv-accent", p.accent || "#d7a64a");
    host.style.setProperty("--qv-scale", String(Math.min(1.4, Math.max(0.8, Number(p.fontScale) || 1))));
    host.dataset.density = p.density === "compact" ? "compact" : "comfortable";
    host.dataset.position = ["left", "right"].includes(p.position) ? p.position : "right";
  }

  async function send(kind, payload = null) {
    return browser.runtime.sendMessage({kind, payload});
  }

  async function observe() {
    setState("OBSERVE", "reobserving main/head/tree");
    const result = await send("OBSERVE_AUTHORITY");
    render(result);
    setState(result.ok ? "OBSERVE" : "HOLD", result.ok ? "fresh repository frame" : result.reason);
  }

  async function blobPayload(blob, mediaType) {
    if (!blob) return null;
    const MAX = 2 * 1024 * 1024;
    if (blob.size > MAX) throw new Error(`${mediaType} exceeds 2 MiB terminal bound`);
    const buffer = await blob.arrayBuffer();
    const bytes = new Uint8Array(buffer);
    let binary = "";
    for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
    return {media_type: mediaType, content_type: blob.type || "application/octet-stream", bytes: blob.size, base64: btoa(binary)};
  }

  async function toggleAudio() {
    const button = $("[data-act=audio]");
    if (audioRecorder && audioRecorder.state === "recording") {
      audioRecorder.stop();
      audioStream.getTracks().forEach(t => t.stop());
      audioStream = null;
      button.textContent = "🎙 Start audio";
      return;
    }
    audioStream = await navigator.mediaDevices.getUserMedia({audio: true, video: false});
    audioChunks = [];
    audioBlob = null;
    audioRecorder = new MediaRecorder(audioStream);
    audioRecorder.ondataavailable = event => { if (event.data.size) audioChunks.push(event.data); };
    audioRecorder.onstop = () => {
      audioBlob = new Blob(audioChunks, {type: audioRecorder.mimeType || "audio/webm"});
      mediaState.textContent = `audio local · ${audioBlob.size} B · explicit Prepare required`;
    };
    audioRecorder.start();
    button.textContent = "■ Stop audio";
    mediaState.textContent = "audio recording locally";
  }

  async function toggleCamera() {
    const button = $("[data-act=camera]");
    if (videoStream) {
      videoStream.getTracks().forEach(t => t.stop());
      videoStream = null;
      video.srcObject = null;
      video.hidden = true;
      snapshotButton.disabled = true;
      button.textContent = "📷 Start camera";
      mediaState.textContent = snapshotBlob ? "snapshot local · explicit Prepare required" : "media local";
      return;
    }
    videoStream = await navigator.mediaDevices.getUserMedia({audio: false, video: {facingMode: "user"}});
    video.srcObject = videoStream;
    video.hidden = false;
    await video.play();
    snapshotButton.disabled = false;
    button.textContent = "■ Stop camera";
    mediaState.textContent = "camera preview local";
  }

  async function takeSnapshot() {
    if (!videoStream || !video.videoWidth) throw new Error("camera preview unavailable");
    const canvas = document.createElement("canvas");
    const maxWidth = 1280;
    const scale = Math.min(1, maxWidth / video.videoWidth);
    canvas.width = Math.round(video.videoWidth * scale);
    canvas.height = Math.round(video.videoHeight * scale);
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    snapshotBlob = await new Promise(resolve => canvas.toBlob(resolve, "image/webp", 0.86));
    if (!snapshotBlob) throw new Error("snapshot encoding failed");
    mediaState.textContent = `video snapshot local · ${snapshotBlob.size} B · explicit Prepare required`;
  }

  async function prepare() {
    setState("PREPARE", "no protected effect");
    commitButton.disabled = true;
    prepared = null;
    preparedRequest = null;
    const request = {
      schema: "qikvrt_terminal_input_v1",
      submitted_at: new Date().toISOString(),
      page: location.href,
      text: command.value,
      audio: await blobPayload(audioBlob, "audio"),
      video: await blobPayload(snapshotBlob, "video_snapshot")
    };
    const result = await send("PREPARE_EFFECT", request);
    prepared = result;
    preparedRequest = request;
    render(result);
    const done = result && result.effect_ack && result.effect_ack.state === "EFFECT_ACK_DONE";
    commitButton.disabled = !done;
    setState(done ? "PREPARED_DONE" : "HOLD", done ? "exact prepared payload frozen for commit" : (result.reason || "non-DONE"));
  }

  async function commit() {
    if (!prepared || !preparedRequest || !prepared.effect_ack || prepared.effect_ack.state !== "EFFECT_ACK_DONE") {
      setState("HOLD", "DONE prepare required");
      return;
    }
    commitButton.disabled = true;
    setState("COMMIT", "exact prepared binding");
    const result = await send("COMMIT_EFFECT", {confirmed: true, prepared, request: preparedRequest});
    render(result);
    setState(result && result.ordinary_release ? "EFFECT_ACK_DONE" : "HOLD", result && result.ordinary_release ? "post-effect reobserve required" : "commit not released");
    prepared = null;
    preparedRequest = null;
    await observe();
  }

  host.addEventListener("click", async event => {
    const button = event.target.closest("button[data-act]");
    if (!button) return;
    try {
      const act = button.dataset.act;
      if (act === "observe") await observe();
      else if (act === "audio") await toggleAudio();
      else if (act === "camera") await toggleCamera();
      else if (act === "snapshot") await takeSnapshot();
      else if (act === "prepare") await prepare();
      else if (act === "commit") await commit();
      else if (act === "options") browser.runtime.openOptionsPage();
      else if (act === "collapse") host.classList.toggle("qv-collapsed");
    } catch (error) {
      setState("HOLD", error.message);
      render({state: "HOLD", reason: error.message, ordinary_release: false});
    }
  });

  applyPreferences().then(observe).catch(error => {
    setState("HOLD", error.message);
    render({state: "HOLD", reason: error.message});
  });
})();
