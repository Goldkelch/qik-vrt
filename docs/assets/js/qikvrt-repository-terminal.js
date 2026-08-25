/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */

(function () {
  "use strict";

  const REPOSITORIES = Object.freeze({
    authority: Object.freeze({
      label: "Authority",
      name: "Goldkelch/qik-vrt",
      branch: "main",
      endpoint: "https://api.github.com/repos/Goldkelch/qik-vrt",
    }),
    mirror: Object.freeze({
      label: "Mirror",
      name: "ingolf-lohmann/qik-vrt",
      branch: "main",
      endpoint: "https://api.github.com/repos/ingolf-lohmann/qik-vrt",
    }),
  });

  const FIXED_DOCUMENTS = Object.freeze({
    ai: Object.freeze({ path: "AI", label: "/AI" }),
    status: Object.freeze({ path: "STATUS.md", label: "STATUS.md" }),
    readme: Object.freeze({ path: "README.md", label: "README.md" }),
    architecture: Object.freeze({ path: "docs/ARCHITECTURE.md", label: "docs/ARCHITECTURE.md" }),
    boundaries: Object.freeze({ path: "docs/BOUNDARIES.md", label: "docs/BOUNDARIES.md" }),
    privacy: Object.freeze({ path: "docs/PRIVACY_PRESERVING_INTERACTION_ARCHIVE.md", label: "docs/PRIVACY_PRESERVING_INTERACTION_ARCHIVE.md" }),
  });

  const UI = {
    de: {
      initial: "Bereit. Nutze help, status, capabilities, read, publications oder analyse.",
      command: "Befehl",
      evidence: "Repository-Evidenz",
      continue: "CONTINUE",
      source: "Quelle",
      noInput: "Bitte gib einen erlaubten Befehl ein.",
      unknown: "Nicht erlaubter Befehl. Nutze help; diese Schnittstelle akzeptiert keine freien Befehle oder URLs.",
      invalidTarget: "Ungültiger Repository-Kontext. Erlaubt sind authority oder mirror.",
      invalidDocument: "Ungültige Dokumentauswahl. Nutze nur die in help gezeigte feste Liste.",
      missingQuestion: "Für analyse fehlt eine Frage oder ein Fall.",
      loading: "Lese öffentliche Repository-Evidenz …",
      voiceUnavailable: "CONTINUE: Die Spracherkennung wird von diesem Browser nicht angeboten. Texteingabe bleibt vollständig verfügbar.",
      voiceReady: "Sprachfunktionen sind optional bereit. Das Mikrofon startet erst nach einem Klick.",
      listening: "Mikrofon aktiv. Sprich einen Befehl oder eine Frage; der Entwurf wird nicht automatisch ausgeführt.",
      stopped: "Spracherkennung beendet.",
      speechUnavailable: "CONTINUE: Browser-Vorlesen ist nicht verfügbar.",
      nothingToSpeak: "Es liegt noch keine Ausgabe zum Vorlesen vor.",
      speaking: "Vorlesen aktiv. Mit „Vorlesen stoppen“ lässt es sich jederzeit unterbrechen.",
      speechStopped: "Vorlesen beendet.",
      asrPrefix: "ASR_DRAFT — nicht verifiziert, nicht gespeichert, vor dem Ausführen prüfen:\n",
      fetchFailure: "Öffentliche Quelle konnte nicht gelesen werden. Netzwerk-, Browser- oder Ratenlimitfehler bleiben CONTINUE und sind kein Evidenzurteil.",
      publicationFailure: "Der lokale Publikationsindex konnte nicht gelesen werden. Das ist CONTINUE; verwende den direkten Publikationslink als Alternative.",
      help: [
        "Erlaubte Befehle:",
        "  help",
        "  status [authority|mirror]",
        "  capabilities [authority|mirror]",
        "  read AI|STATUS|README|ARCHITECTURE|BOUNDARIES|PRIVACY",
        "  publications",
        "  analyse <Frage>  /  analyze <question>",
        "  clear",
        "",
        "Grenze: Nur fest verdrahtete öffentliche GET-Lesewege. Keine freien URLs, keine Zugangsdaten, keine Workflow-Auslösung und keine Schreiboperation.",
      ].join("\n"),
    },
    en: {
      initial: "Ready. Use help, status, capabilities, read, publications, or analyze.",
      command: "Command",
      evidence: "Repository evidence",
      continue: "CONTINUE",
      source: "Source",
      noInput: "Enter an allowed command.",
      unknown: "Command not allowed. Use help; this interface accepts no free-form commands or URLs.",
      invalidTarget: "Invalid repository context. Only authority or mirror are allowed.",
      invalidDocument: "Invalid document selection. Use only the fixed list shown by help.",
      missingQuestion: "analyze needs a question or case.",
      loading: "Reading public repository evidence …",
      voiceUnavailable: "CONTINUE: This browser does not offer speech recognition. Text input remains fully available.",
      voiceReady: "Optional voice features are ready. The microphone starts only after a click.",
      listening: "Microphone active. Speak a command or question; the draft will not run automatically.",
      stopped: "Speech recognition stopped.",
      speechUnavailable: "CONTINUE: Browser speech output is unavailable.",
      nothingToSpeak: "There is no output to read aloud yet.",
      speaking: "Reading aloud. Use Stop reading at any time to interrupt it.",
      speechStopped: "Reading stopped.",
      asrPrefix: "ASR_DRAFT — unverified, not stored, review before running:\n",
      fetchFailure: "The public source could not be read. Network, browser, or rate-limit failures remain CONTINUE and are not an evidence judgment.",
      publicationFailure: "The local publication index could not be read. This is CONTINUE; use the direct publication link as an alternative.",
      help: [
        "Allowed commands:",
        "  help",
        "  status [authority|mirror]",
        "  capabilities [authority|mirror]",
        "  read AI|STATUS|README|ARCHITECTURE|BOUNDARIES|PRIVACY",
        "  publications",
        "  analyse <Frage>  /  analyze <question>",
        "  clear",
        "",
        "Boundary: only fixed public GET read paths. No free-form URLs, credentials, workflow dispatch, or write operation.",
      ].join("\n"),
    },
  };

  const state = {
    locale: "de",
    repositoryKey: "authority",
    lastOutput: "",
    recognition: null,
  };

  function byId(identifier) {
    return document.getElementById(identifier);
  }

  function message(key) {
    return UI[state.locale][key];
  }

  function currentRepository() {
    return REPOSITORIES[state.repositoryKey];
  }

  function timestamp() {
    return new Intl.DateTimeFormat(state.locale === "de" ? "de-DE" : "en-GB", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(new Date());
  }

  function setConnectionState(value) {
    byId("terminalConnectionState").textContent = value;
  }

  function appendEntry(kind, heading, body, sourceUrl) {
    const output = byId("terminalOutput");
    const entry = document.createElement("article");
    const header = document.createElement("div");
    const title = document.createElement("h4");
    const time = document.createElement("time");
    const content = document.createElement("pre");

    entry.className = "terminal-entry";
    entry.dataset.kind = kind;
    header.className = "terminal-entry-header";
    title.textContent = heading;
    time.textContent = timestamp();
    time.dateTime = new Date().toISOString();
    content.textContent = body;
    header.append(title, time);
    entry.append(header, content);

    if (sourceUrl) {
      const source = document.createElement("a");
      source.href = sourceUrl;
      source.target = "_blank";
      source.rel = "noopener";
      source.textContent = `${message("source")}: ${sourceUrl}`;
      entry.append(source);
    }

    output.append(entry);
    output.scrollTop = output.scrollHeight;
    state.lastOutput = body;
  }

  function clearOutput() {
    const output = byId("terminalOutput");
    output.replaceChildren();
    appendEntry("evidence", message("evidence"), message("initial"));
    setConnectionState("LOCAL_READY");
  }

  function setLanguage(locale) {
    state.locale = locale;
    document.documentElement.dataset.language = locale;
    document.documentElement.lang = locale;
    const toggle = byId("languageToggle");
    toggle.textContent = locale === "de" ? "English" : "Deutsch";
    toggle.setAttribute("aria-pressed", String(locale === "en"));
    byId("terminalInput").placeholder = "status";
  }

  function setTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("qikvrt-theme", theme);
  }

  function initializeTheme() {
    setTheme(localStorage.getItem("qikvrt-theme") || "dark");
    byId("themeToggle").addEventListener("click", function () {
      setTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark");
    });
  }

  function publicUrl(repository, path) {
    return `https://github.com/${repository.name}/blob/${repository.branch}/${path}`;
  }

  async function publicGet(repository, path) {
    const response = await fetch(`${repository.endpoint}${path}`, {
      method: "GET",
      credentials: "omit",
      headers: { Accept: "application/vnd.github+json" },
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return response.json();
  }

  function decodeContent(content) {
    const compact = String(content || "").replace(/\s/g, "");
    const binary = window.atob(compact);
    const bytes = Uint8Array.from(binary, function (character) {
      return character.charCodeAt(0);
    });
    return new TextDecoder().decode(bytes);
  }

  function boundedText(value, maximum) {
    const text = String(value || "");
    if (text.length <= maximum) {
      return text;
    }
    return `${text.slice(0, maximum)}\n\n[… ${text.length - maximum} additional characters omitted in this terminal view …]`;
  }

  function resolveTarget(value) {
    if (!value) {
      return state.repositoryKey;
    }
    const key = value.toLowerCase();
    return Object.prototype.hasOwnProperty.call(REPOSITORIES, key) ? key : null;
  }

  async function showStatus(target) {
    const key = resolveTarget(target);
    if (!key) {
      appendEntry("continue", message("continue"), message("invalidTarget"));
      return;
    }
    const repository = REPOSITORIES[key];
    setConnectionState("PUBLIC_READ_PENDING");
    appendEntry("command", message("command"), `${message("loading")}\n${repository.name}`);
    try {
      const responses = await Promise.all([
        publicGet(repository, ""),
        publicGet(repository, `/commits/${repository.branch}`),
      ]);
      const metadata = responses[0];
      const commit = responses[1];
      const tree = commit && commit.commit && commit.commit.tree ? commit.commit.tree.sha : "UNAVAILABLE";
      const output = [
        `Repository: ${repository.name}`,
        `Role: ${repository.label}`,
        `Ref: ${repository.branch}`,
        `Commit: ${commit.sha || "UNAVAILABLE"}`,
        `Tree: ${tree}`,
        `Visibility: ${metadata.visibility || "UNAVAILABLE"}`,
        `Updated: ${metadata.updated_at || "UNAVAILABLE"}`,
        "Read mode: PUBLIC_GET_ONLY",
        "Effect state: EFFECT_ACK_CONTINUE",
      ].join("\n");
      appendEntry("evidence", message("evidence"), output, `https://github.com/${repository.name}/commits/${repository.branch}`);
      setConnectionState("PUBLIC_READ_COMPLETE");
    } catch (error) {
      appendEntry("continue", message("continue"), `${message("fetchFailure")}\n${String(error.message || error)}`);
      setConnectionState("CONTINUE");
    }
  }

  async function showCapabilities(target) {
    const key = resolveTarget(target);
    if (!key) {
      appendEntry("continue", message("continue"), message("invalidTarget"));
      return;
    }
    const repository = REPOSITORIES[key];
    const path = ".well-known/qik-vrt-self-disclosure.json";
    setConnectionState("PUBLIC_READ_PENDING");
    try {
      const payload = await publicGet(repository, `/contents/${path}?ref=${repository.branch}`);
      const parsed = JSON.parse(decodeContent(payload.content));
      const capabilityIds = Array.isArray(parsed.capabilities)
        ? parsed.capabilities.map(function (item) {
          return typeof item === "string" ? item : item && item.id ? item.id : "UNAVAILABLE";
        }).join(", ")
        : "UNAVAILABLE";
      const completion = parsed.completion_claims || {};
      const output = [
        `Repository: ${repository.name}`,
        `Disclosure path: ${path}`,
        `Schema: ${parsed.schema || "UNAVAILABLE"}`,
        `State: ${parsed.state || "UNAVAILABLE"}`,
        `Capabilities: ${capabilityIds}`,
        `Completion claims: PASS=${String(completion.pass)}, FINAL_PASS=${String(completion.final_pass)}, EFFECT_ACK_DONE=${String(completion.effect_ack_done)}`,
        "Interpretation: self-disclosure is repository evidence, not independent certification.",
      ].join("\n");
      appendEntry("evidence", message("evidence"), output, publicUrl(repository, path));
      setConnectionState("PUBLIC_READ_COMPLETE");
    } catch (error) {
      appendEntry("continue", message("continue"), `${message("fetchFailure")}\n${String(error.message || error)}`);
      setConnectionState("CONTINUE");
    }
  }

  async function showDocument(name) {
    const documentKey = String(name || "").toLowerCase();
    const source = FIXED_DOCUMENTS[documentKey];
    if (!source) {
      appendEntry("continue", message("continue"), message("invalidDocument"));
      return;
    }
    const repository = currentRepository();
    setConnectionState("PUBLIC_READ_PENDING");
    try {
      const payload = await publicGet(repository, `/contents/${source.path}?ref=${repository.branch}`);
      const text = decodeContent(payload.content);
      const output = [
        `Repository: ${repository.name}`,
        `Ref: ${repository.branch}`,
        `Path: ${source.path}`,
        `Blob: ${payload.sha || "UNAVAILABLE"}`,
        "",
        boundedText(text, 7000),
      ].join("\n");
      appendEntry("evidence", `${message("evidence")}: ${source.label}`, output, publicUrl(repository, source.path));
      setConnectionState("PUBLIC_READ_COMPLETE");
    } catch (error) {
      appendEntry("continue", message("continue"), `${message("fetchFailure")}\n${String(error.message || error)}`);
      setConnectionState("CONTINUE");
    }
  }

  async function showPublications() {
    setConnectionState("LOCAL_READ_PENDING");
    try {
      const response = await fetch("../publications/index.json", {
        method: "GET",
        credentials: "omit",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const index = await response.json();
      const items = Array.isArray(index.publication_bundles)
        ? index.publication_bundles
        : Array.isArray(index.items)
          ? index.items
          : Array.isArray(index.publications)
            ? index.publications
            : [];
      const lines = [
        "Source: docs/publications/index.json",
        `Entries: ${items.length}`,
        "Read mode: SAME_ORIGIN_GET_ONLY",
        "",
      ];
      items.slice(0, 12).forEach(function (item, indexPosition) {
        const title = item.title || item.name || item.id || "UNNAMED";
        const locator = item.url || item.path || item.doi || "UNAVAILABLE";
        lines.push(`${indexPosition + 1}. ${title}\n   ${locator}`);
      });
      if (items.length > 12) {
        lines.push(`\n[… ${items.length - 12} further entries remain in the full index …]`);
      }
      appendEntry("evidence", message("evidence"), lines.join("\n"), "../publications/");
      setConnectionState("LOCAL_READ_COMPLETE");
    } catch (error) {
      appendEntry("continue", message("continue"), `${message("publicationFailure")}\n${String(error.message || error)}`);
      setConnectionState("CONTINUE");
    }
  }

  async function runLocalAnalysis(question) {
    if (!question) {
      appendEntry("continue", message("continue"), message("missingQuestion"));
      return;
    }
    if (!window.QIKVRTLocalEngine) {
      appendEntry("continue", message("continue"), "CONTINUE: The local rule engine is unavailable; repository reading remains available.");
      return;
    }
    setConnectionState("LOCAL_ANALYSIS_PENDING");
    try {
      const response = window.QIKVRTLocalEngine.answerLocal(question, null);
      appendEntry("evidence", `${message("evidence")}: LOCAL_RULE_ANALYSIS`, response, "../");
      setConnectionState("LOCAL_ANALYSIS_COMPLETE");
    } catch (error) {
      appendEntry("continue", message("continue"), `CONTINUE: Local analysis could not complete.\n${String(error.message || error)}`);
      setConnectionState("CONTINUE");
    }
  }

  async function runCommand(value) {
    const raw = String(value || "").trim();
    if (!raw) {
      appendEntry("continue", message("continue"), message("noInput"));
      return;
    }
    const parts = raw.split(/\s+/);
    const command = parts[0].toLowerCase();
    const argument = parts.slice(1).join(" ");
    appendEntry("command", message("command"), raw);

    if (command === "help") {
      appendEntry("evidence", message("evidence"), message("help"));
      return;
    }
    if (command === "clear") {
      clearOutput();
      return;
    }
    if (command === "status") {
      await showStatus(argument || undefined);
      return;
    }
    if (command === "capabilities") {
      await showCapabilities(argument || undefined);
      return;
    }
    if (command === "read") {
      await showDocument(argument);
      return;
    }
    if (command === "publications") {
      await showPublications();
      return;
    }
    if (command === "analyse" || command === "analyze") {
      await runLocalAnalysis(argument);
      return;
    }
    appendEntry("continue", message("continue"), message("unknown"));
  }

  function configureVoice() {
    const start = byId("startListening");
    const stop = byId("stopListening");
    const speak = byId("speakOutput");
    const stopSpeak = byId("stopSpeaking");
    const voiceStatus = byId("voiceStatus");
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    stop.disabled = true;
    if (Recognition) {
      voiceStatus.textContent = message("voiceReady");
      start.addEventListener("click", function () {
        if (state.recognition) {
          return;
        }
        const recognition = new Recognition();
        recognition.lang = state.locale === "de" ? "de-DE" : "en-GB";
        recognition.interimResults = true;
        recognition.continuous = false;
        recognition.onstart = function () {
          start.disabled = true;
          stop.disabled = false;
          voiceStatus.textContent = message("listening");
        };
        recognition.onresult = function (event) {
          let draftText = "";
          for (let index = event.resultIndex; index < event.results.length; index += 1) {
            draftText += event.results[index][0].transcript;
          }
          const draft = byId("asrDraft");
          draft.hidden = false;
          draft.textContent = `${message("asrPrefix")}${draftText.trim()}`;
          byId("terminalInput").value = draftText.trim();
        };
        recognition.onerror = function (event) {
          voiceStatus.textContent = `CONTINUE: Speech recognition reported ${event.error || "an unknown error"}.`;
        };
        recognition.onend = function () {
          state.recognition = null;
          start.disabled = false;
          stop.disabled = true;
          if (voiceStatus.textContent === message("listening")) {
            voiceStatus.textContent = message("stopped");
          }
        };
        state.recognition = recognition;
        recognition.start();
      });
      stop.addEventListener("click", function () {
        if (state.recognition) {
          state.recognition.stop();
        }
      });
    } else {
      start.disabled = true;
      stop.disabled = true;
      voiceStatus.textContent = message("voiceUnavailable");
    }

    if (!("speechSynthesis" in window)) {
      speak.disabled = true;
      stopSpeak.disabled = true;
    }
    speak.addEventListener("click", function () {
      if (!("speechSynthesis" in window)) {
        voiceStatus.textContent = message("speechUnavailable");
        return;
      }
      if (!state.lastOutput) {
        voiceStatus.textContent = message("nothingToSpeak");
        return;
      }
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(state.lastOutput);
      utterance.lang = state.locale === "de" ? "de-DE" : "en-GB";
      utterance.onend = function () {
        voiceStatus.textContent = message("stopped");
      };
      window.speechSynthesis.speak(utterance);
      voiceStatus.textContent = message("speaking");
    });
    stopSpeak.addEventListener("click", function () {
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
      voiceStatus.textContent = message("speechStopped");
    });
  }

  function initialize() {
    setLanguage("de");
    initializeTheme();
    clearOutput();
    byId("languageToggle").addEventListener("click", function () {
      setLanguage(state.locale === "de" ? "en" : "de");
    });
    byId("repositorySelect").addEventListener("change", function (event) {
      state.repositoryKey = event.target.value;
      setConnectionState("LOCAL_READY");
    });
    byId("terminalForm").addEventListener("submit", function (event) {
      event.preventDefault();
      runCommand(byId("terminalInput").value);
    });
    byId("terminalInput").addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        runCommand(event.currentTarget.value);
      }
    });
    byId("clearCommand").addEventListener("click", clearOutput);
    document.querySelectorAll(".terminal-command").forEach(function (button) {
      button.addEventListener("click", function () {
        byId("terminalInput").value = button.dataset.command || "";
        byId("terminalInput").focus();
      });
    });
    configureVoice();
  }

  document.addEventListener("DOMContentLoaded", initialize);
})();
