(() => {
  const p = new URLSearchParams(location.search);
  if (p.get("qikvrt_effect") !== "review_approve") return;

  const expectedOwner = p.get("qikvrt_owner");
  const expectedRepo = p.get("qikvrt_repo");
  const expectedPr = p.get("qikvrt_pr");
  const expectedHead = p.get("qikvrt_head");
  const expectedTree = p.get("qikvrt_tree");
  const key = `qikvrt-review:${expectedPr}:${expectedHead}:${expectedTree}`;

  const hold = reason => {
    console.error("QIKVRT_REVIEW_EFFECT_HOLD", reason);
    document.documentElement.dataset.qikvrtReviewEffect = `HOLD:${reason}`;
  };

  const clickByText = (selector, text) => {
    const node = [...document.querySelectorAll(selector)].find(el => (el.textContent || "").trim().includes(text));
    if (!node) throw new Error(`missing control: ${text}`);
    node.click();
    return node;
  };

  const wait = ms => new Promise(resolve => setTimeout(resolve, ms));

  async function run() {
    if (sessionStorage.getItem(key) === "submitted") return;
    if (expectedOwner !== "Goldkelch" || expectedRepo !== "Goldkelch/qik-vrt") throw new Error("owner/repository binding mismatch");
    if (!/^\d+$/.test(expectedPr || "") || !/^[0-9a-f]{40}$/.test(expectedHead || "") || !/^[0-9a-f]{40}$/.test(expectedTree || "")) {
      throw new Error("invalid exact binding");
    }

    const loginMeta = document.querySelector('meta[name="user-login"]');
    const observedLogin = loginMeta && loginMeta.getAttribute("content");
    if (observedLogin !== expectedOwner) throw new Error(`authenticated principal mismatch: ${observedLogin || "none"}`);

    const pr = await fetch(`https://api.github.com/repos/Goldkelch/qik-vrt/pulls/${expectedPr}`, {headers: {Accept: "application/vnd.github+json"}}).then(r => {
      if (!r.ok) throw new Error(`PR reobservation HTTP ${r.status}`);
      return r.json();
    });
    if (!pr.head || pr.head.sha !== expectedHead) throw new Error("PR head drift");

    const commit = await fetch(`https://api.github.com/repos/Goldkelch/qik-vrt/git/commits/${expectedHead}`, {headers: {Accept: "application/vnd.github+json"}}).then(r => {
      if (!r.ok) throw new Error(`tree reobservation HTTP ${r.status}`);
      return r.json();
    });
    if (!commit.tree || commit.tree.sha !== expectedTree) throw new Error("PR tree drift");

    clickByText("button,summary", "Review changes");
    await wait(250);

    const approve = [...document.querySelectorAll('input[type="radio"]')].find(el => {
      const label = el.closest("label") || document.querySelector(`label[for="${el.id}"]`);
      return label && /Approve/i.test(label.textContent || "");
    });
    if (!approve) throw new Error("Approve option unavailable");
    approve.click();
    await wait(100);

    clickByText('button[type="submit"],button', "Submit review");
    sessionStorage.setItem(key, "submitted");
    document.documentElement.dataset.qikvrtReviewEffect = "SUBMITTED_REOBSERVE_REQUIRED";
  }

  run().catch(error => hold(error.message));
})();
