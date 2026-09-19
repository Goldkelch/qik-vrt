(() => {
  if (document.getElementById("qikvrt-ai-terminal-host")) return;

  const message = (name, substitutions) => browser.i18n.getMessage(name, substitutions);

  const host = document.createElement("section");
  host.id = "qikvrt-ai-terminal-host";
  host.lang = browser.i18n.getMessage("@@ui_locale").replaceAll("_", "-");
  host.dir = browser.i18n.getMessage("@@bidi_dir");
  host.setAttribute("aria-label", "QIKVRT AI Terminal");
  host.innerHTML = `
    <header class="qv-head">
      <div><strong>QIKVRT · AI TERMINAL</strong><small data-i18n="subtitle"></small></div>
      <div class="qv-head-actions"><button data-act="observe" data-i18n="observe"></button><button data-act="options" data-i18n-label="personalize">⚙</button><button data-act="collapse" data-i18n-label="collapse">—</button></div>
    </header>
    <div class="qv-body">
      <div class="qv-status" data-role="status">OBSERVE</div>
      <pre class="qv-output" data-role="output" dir="auto" aria-live="polite" data-i18n="initialized"></pre>
      <label class="qv-label" for="qv-command" data-i18n="input"></label>
      <textarea id="qv-command" data-role="command" rows="3" dir="auto"></textarea>
      <div class="qv-media-row">
        <button data-act="audio" data-i18n="audioStart"></button>
        <button data-act="camera" data-i18n="cameraStart"></button>
        <button data-act="snapshot" data-i18n="snapshot" disabled></button>
        <span data-role="media-state" data-i18n="mediaLocal"></span>
      </div>
      <video data-role="video" playsinline muted hidden></video>
      <div class="qv-effect-row">
        <button class="qv-prepare" data-act="prepare" data-i18n="prepare"></button>
        <button class="qv-commit" data-act="commit" data-i18n="commit" disabled></button>
        <span data-i18n="prepareBoundary"></span>
      </div>
    </div>`;
  document.body.appendChild(host);
  // Prepare ≠ effect. Translations are text only; protocol values stay canonical.
  host.querySelectorAll("[data-i18n]").forEach(node => {
    node.textContent = message(node.dataset.i18n);
  });
  host.querySelectorAll("[data-i18n-label]").forEach(node => {
    node.setAttribute("aria-label", message(node.dataset.i18nLabel));
  });

  const $ = selector => host.querySelector(selector);
  const output = $("[data-role=output]");
  const status = $("[data-role=status]");
  const command = $("[data-role=command]");
  command.placeholder = message("inputHint");
  const video = $("[data-role=video]");
  const mediaState = $("[data-role=media-state]");
  const commitButton = $("[data-act=commit]");
  const snapshotButton = $("[data-act=snapshot]");

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
    setState("OBSERVE", message("observing"));
    const result = await send("OBSERVE_AUTHORITY");
    render(result);
    setState(result.ok ? "OBSERVE" : "HOLD", result.ok ? message("observed") : result.reason);
  }

  async function blobPayload(blob, mediaType) {
    if (!blob) return null;
    const MAX = 2 * 1024 * 1024;
    if (blob.size > MAX) throw new Error(message("tooLarge"));
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
      button.textContent = message("audioStart");
      return;
    }
    audioStream = await navigator.mediaDevices.getUserMedia({audio: true, video: false});
    audioChunks = [];
    audioBlob = null;
    audioRecorder = new MediaRecorder(audioStream);
    audioRecorder.ondataavailable = event => { if (event.data.size) audioChunks.push(event.data); };
    audioRecorder.onstop = () => {
      audioBlob = new Blob(audioChunks, {type: audioRecorder.mimeType || "audio/webm"});
      mediaState.textContent = message("audioLocal", String(audioBlob.size));
    };
    audioRecorder.start();
    button.textContent = message("audioStop");
    mediaState.textContent = message("audioRecording");
  }

  async function toggleCamera() {
    const button = $("[data-act=camera]");
    if (videoStream) {
      videoStream.getTracks().forEach(t => t.stop());
      videoStream = null;
      video.srcObject = null;
      video.hidden = true;
      snapshotButton.disabled = true;
      button.textContent = message("cameraStart");
      mediaState.textContent = snapshotBlob ? message("snapshotLocal", String(snapshotBlob.size)) : message("mediaLocal");
      return;
    }
    videoStream = await navigator.mediaDevices.getUserMedia({audio: false, video: {facingMode: "user"}});
    video.srcObject = videoStream;
    video.hidden = false;
    await video.play();
    snapshotButton.disabled = false;
    button.textContent = message("cameraStop");
    mediaState.textContent = message("cameraPreview");
  }

  async function takeSnapshot() {
    if (!videoStream || !video.videoWidth) throw new Error(message("cameraUnavailable"));
    const canvas = document.createElement("canvas");
    const maxWidth = 1280;
    const scale = Math.min(1, maxWidth / video.videoWidth);
    canvas.width = Math.round(video.videoWidth * scale);
    canvas.height = Math.round(video.videoHeight * scale);
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    snapshotBlob = await new Promise(resolve => canvas.toBlob(resolve, "image/webp", 0.86));
    if (!snapshotBlob) throw new Error(message("snapshotFailed"));
    mediaState.textContent = message("snapshotLocal", String(snapshotBlob.size));
  }

  async function prepare() {
    setState("PREPARE", message("preparing"));
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
    setState(done ? "PREPARED_DONE" : "HOLD", done ? message("prepared") : (result.reason || "non-DONE"));
  }

  async function commit() {
    if (!prepared || !preparedRequest || !prepared.effect_ack || prepared.effect_ack.state !== "EFFECT_ACK_DONE") {
      setState("HOLD", message("prepareRequired"));
      return;
    }
    commitButton.disabled = true;
    setState("COMMIT", message("committing"));
    const result = await send("COMMIT_EFFECT", {confirmed: true, prepared, request: preparedRequest});
    render(result);
    setState(result && result.ordinary_release ? "EFFECT_ACK_DONE" : "HOLD", result && result.ordinary_release ? message("readbackRequired") : message("notReleased"));
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
