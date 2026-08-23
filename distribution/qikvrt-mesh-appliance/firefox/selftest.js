/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
(async () => {
  "use strict";
  const node = document.getElementById("qikvrt-selftest");
  try {
    const request = {
      schema: "qikvrt_terminal_input_v1",
      input_id: "qikvrt-mesh-appliance-firefox-selftest",
      text: "QIK-VRT Mesh Appliance browser prepare commit selftest",
      audio: null,
      video: null
    };
    const discovery = await browser.runtime.sendMessage({kind: "DISCOVER_EFFECT_ACK"});
    if (!discovery || discovery.discovered !== true) throw new Error("Effect-Ack capability discovery failed");

    const prepared = await browser.runtime.sendMessage({kind: "PREPARE_EFFECT", payload: request});
    if (!prepared || prepared.record_validated !== true || !prepared.effect_ack || prepared.effect_ack.state !== "EFFECT_ACK_DONE") {
      throw new Error(prepared && prepared.reason ? prepared.reason : "prepare record was not validated DONE");
    }
    if (prepared.ordinary_release === true) throw new Error("prepare must not itself execute the effect");

    const committed = await browser.runtime.sendMessage({
      kind: "COMMIT_EFFECT",
      payload: {confirmed: true, prepared, request}
    });
    if (!committed || committed.ordinary_release !== true || !committed.effect_ack || committed.effect_ack.state !== "EFFECT_ACK_DONE") {
      throw new Error(committed && committed.reason ? committed.reason : "commit did not reach bounded DONE");
    }
    const postEffect = committed.body && committed.body.post_effect;
    if (!postEffect || postEffect.kind !== "TERMINAL_INPUT_ACCEPTED" || postEffect.external_effect !== "NONE") {
      throw new Error("bounded terminal-input post-effect receipt unavailable");
    }

    const observed = await browser.runtime.sendMessage({kind: "OBSERVE_EFFECT_STATE"});
    const state = observed && observed.body;
    if (!observed || observed.http_status !== 200 || !state || state.events < 1 || !state.last_event) {
      throw new Error("post-effect backend state unavailable");
    }
    if (state.last_event.protocol_hash !== postEffect.protocol_hash || state.last_event.kind !== "TERMINAL_INPUT_ACCEPTED") {
      throw new Error("post-effect reobservation does not bind committed event");
    }
    if (state.external_effect !== "NONE") throw new Error("external effect boundary changed");

    node.dataset.state = "EFFECT_ACK_DONE";
    node.textContent = JSON.stringify({
      schema: "qikvrt_firefox_effect_ack_selftest_v2",
      browser_execution_observed: true,
      protocol_validation_observed: true,
      prepare_observed: true,
      commit_observed: true,
      post_effect_reobservation_observed: true,
      bounded_loopback_terminal_input_acknowledged: true,
      state: "EFFECT_ACK_DONE",
      protocol_hash: state.last_event.protocol_hash,
      event_id: state.last_event.event_id,
      external_effect: "NONE"
    }, null, 2);
  } catch (error) {
    node.dataset.state = "HOLD";
    node.textContent = JSON.stringify({
      schema: "qikvrt_firefox_effect_ack_selftest_v2",
      state: "HOLD",
      reason: String(error),
      external_effect: "NONE"
    }, null, 2);
  }
})();
