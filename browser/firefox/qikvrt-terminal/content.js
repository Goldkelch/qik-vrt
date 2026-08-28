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
      <div class="qv-effect-row qv-peer-row">
        <button class="qv-peer-prepare" data-act="peer-prepare">V2 Peer Prepare</button>
        <button class="qv-peer-commit" data-act="peer-commit" disabled>V2 Peer Commit</button>
        <span>closed JSON · configured 127.0.0.1 peer only · no external effect</span>
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
  const peerCommitButton = $("[data-act=peer-commit]");
  const snapshotButton = $("[data-act=snapshot]");

  let audioStream = null;
  let audioRecorder = null;
  let audioChunks = [];
  let audioBlob = null;
  let videoStream = null;
  let snapshotBlob = null;
  let prepared = null;
  let preparedRequest = null;
  let peerPrepared = null;

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

  async function peerPrepare() {
    setState("PEER_PREPARE", "explicit local V2 request only");
    peerCommitButton.disabled = true;
    peerPrepared = null;
    const request = {
      schema: "qikvrt_terminal_input_v2",
      submitted_at: new Date().toISOString(),
      page: location.href,
      text: command.value,
      audio: await blobPayload(audioBlob, "audio"),
      video: await blobPayload(snapshotBlob, "video_snapshot")
    };
    const result = await send("PREPARE_PEER_V2", request);
    peerPrepared = result;
    render(result);
    const ready = result && result.record_validated === true && result.ordinary_release === false;
    peerCommitButton.disabled = !ready;
    setState(ready ? "PEER_PREPARED" : "HOLD", ready ? "explicit V2 local commit remains required" : (result.reason || "V2 peer prepare not validated"));
  }

  async function peerCommit() {
    if (!peerPrepared || peerPrepared.record_validated !== true) {
      setState("HOLD", "validated V2 peer prepare required");
      return;
    }
    peerCommitButton.disabled = true;
    setState("PEER_COMMIT", "explicit local V2 request and record reobservation");
    const result = await send("COMMIT_PEER_V2", {confirmed: true, prepared: peerPrepared});
    render(result);
    setState(result && result.local_commit_receipt ? "PEER_LOCAL_COMMITTED" : "HOLD", result && result.local_commit_receipt ? "local ledger receipt; external effect remains NONE" : (result.reason || "V2 local commit not validated"));
    peerPrepared = null;
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
      else if (act === "peer-prepare") await peerPrepare();
      else if (act === "peer-commit") await peerCommit();
      else if (act === "options") browser.runtime.openOptionsPage();
      else if (act === "collapse") host.classList.toggle("qv-collapsed");
    } catch (error) {
      setState("HOLD", error.message);
      render({state: "HOLD", reason: error.message, ordinary_release: false});
    }
  });

  applyPreferences().then(() => {
    setState("READY", "explicit Observe required");
  }).catch(error => {
    setState("HOLD", error.message);
    render({state: "HOLD", reason: error.message});
  });
})();
