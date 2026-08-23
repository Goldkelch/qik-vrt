/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Bounded appliance-only startup probe. No repository or external effect. */
(async () => {
  const receipt = {
    schema: "qikvrt_appliance_firefox_probe_v1",
    started_at: new Date().toISOString(),
    external_effect: "NONE",
    ordinary_release: false,
    state: "HOLD"
  };
  try {
    await new Promise(resolve => setTimeout(resolve, 750));
    const request = {
      schema: "qikvrt_terminal_input_v1",
      text: "QIKVRT_APPLIANCE_FIREFOX_SMOKE",
      audio: null,
      video: null
    };
    const prepared = await prepareEffect(request);
    if (!prepared || prepared.record_validated !== true || prepared.ordinary_release !== false) {
      throw new Error("prepare did not produce a validated bounded record");
    }
    const committed = await commitEffect({confirmed: true, prepared, request});
    if (!committed || committed.ordinary_release !== true ||
        !committed.effect_ack || committed.effect_ack.state !== "EFFECT_ACK_DONE") {
      throw new Error("commit did not reach bounded EFFECT_ACK_DONE");
    }
    receipt.state = "BOUNDED_LOOPBACK_TERMINAL_INPUT_ACKNOWLEDGED";
    receipt.ordinary_release = true;
    receipt.record_hash = committed.effect_ack.record_hash;
    receipt.http_status = committed.http_status;
  } catch (error) {
    receipt.state = "HOLD";
    receipt.reason = String(error && error.message ? error.message : error);
  }
  receipt.completed_at = new Date().toISOString();
  await browser.storage.local.set({qikvrtApplianceFirefoxReceipt: receipt});
})();
