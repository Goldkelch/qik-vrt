/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */

(function () {
  "use strict";

  const OUTPUT_ID = "terminalOutput";

  function languageIsGerman() {
    return document.documentElement.dataset.language !== "en";
  }

  function copyLabel() {
    return languageIsGerman() ? "Markdown kopieren" : "Copy Markdown";
  }

  function copiedLabel() {
    return languageIsGerman() ? "Kopiert" : "Copied";
  }

  function enhanceEntry(entry) {
    if (!(entry instanceof HTMLElement) || !entry.classList.contains("terminal-entry") || entry.dataset.collapsible === "true") {
      return;
    }

    const header = entry.querySelector(":scope > .terminal-entry-header");
    const content = entry.querySelector(":scope > pre");
    if (!header || !content) {
      return;
    }

    const details = document.createElement("details");
    const summary = document.createElement("summary");
    const summaryText = document.createElement("span");
    const heading = header.querySelector("h4");
    const time = header.querySelector("time");
    const controls = document.createElement("span");
    const copy = document.createElement("button");

    details.className = "terminal-entry-details";
    summary.className = "terminal-entry-summary";
    summaryText.className = "terminal-entry-summary-text";
    controls.className = "terminal-entry-controls";
    copy.className = "btn terminal-copy-output";
    copy.type = "button";
    copy.textContent = copyLabel();

    summaryText.textContent = heading ? heading.textContent : "Output";
    if (time) {
      const timeText = document.createElement("span");
      timeText.className = "terminal-entry-summary-time";
      timeText.textContent = time.textContent;
      summaryText.append(" ", timeText);
    }

    copy.addEventListener("click", async function (event) {
      event.preventDefault();
      event.stopPropagation();
      try {
        await navigator.clipboard.writeText(content.textContent || "");
        copy.textContent = copiedLabel();
        window.setTimeout(function () {
          copy.textContent = copyLabel();
        }, 1600);
      } catch (error) {
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(content);
        selection.removeAllRanges();
        selection.addRange(range);
      }
    });

    summary.append(summaryText);
    controls.append(copy);
    details.append(summary, controls, content);
    header.remove();
    entry.prepend(details);
    entry.dataset.collapsible = "true";
  }

  function enhanceAll(output) {
    output.querySelectorAll(":scope > .terminal-entry").forEach(enhanceEntry);
  }

  function initialize() {
    const output = document.getElementById(OUTPUT_ID);
    if (!output) {
      return;
    }

    enhanceAll(output);
    const observer = new MutationObserver(function () {
      enhanceAll(output);
    });
    observer.observe(output, { childList: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, { once: true });
  } else {
    initialize();
  }
}());
