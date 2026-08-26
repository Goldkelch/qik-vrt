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

  const wait = ms => new Promise(resolve => setTimeout(resolve, ms));

  async function waitFor(getNode, description, timeoutMs = 5000) {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const node = getNode();
      if (node) return node;
      await wait(100);
    }
    throw new Error(`missing control: ${description}`);
  }

  const byText = (selector, pattern) =>
    [...document.querySelectorAll(selector)].find(el => pattern.test((el.textContent || "").trim()));

  async function observeJson(url, label) {
    const response = await fetch(url, {headers: {Accept: "application/vnd.github+json"}});
    if (!response.ok) throw new Error(`${label} HTTP ${response.status}`);
    return response.json();
  }

  async function run() {
    if (sessionStorage.getItem(key) === "submitted") return;
    if (expectedOwner !== "Goldkelch" || expectedRepo !== "Goldkelch/qik-vrt") {
      throw new Error("owner/repository binding mismatch");
    }
    if (!/^\d+$/.test(expectedPr || "") || !/^[0-9a-f]{40}$/.test(expectedHead || "") || !/^[0-9a-f]{40}$/.test(expectedTree || "")) {
      throw new Error("invalid exact binding");
    }
    if (location.pathname.replace(/\/$/, "") !== `/Goldkelch/qik-vrt/pull/${expectedPr}/files`) {
      throw new Error("PR page binding mismatch");
    }

    const loginMeta = document.querySelector('meta[name="user-login"]');
    const observedLogin = loginMeta && loginMeta.getAttribute("content");
    if (observedLogin !== expectedOwner) {
      throw new Error(`authenticated principal mismatch: ${observedLogin || "none"}`);
    }

    const pr = await observeJson(
      `https://api.github.com/repos/Goldkelch/qik-vrt/pulls/${expectedPr}`,
      "PR reobservation",
    );
    if (pr.state !== "open" || pr.draft === true || pr.base?.ref !== "main") {
      throw new Error("PR is not an open review-ready main candidate");
    }
    if (pr.head?.repo?.full_name !== expectedRepo || pr.head.sha !== expectedHead) {
      throw new Error("PR head drift");
    }
    if (!(pr.requested_reviewers || []).some(reviewer => reviewer.login === expectedOwner)) {
      throw new Error("owner review is not currently requested");
    }

    const commit = await observeJson(
      `https://api.github.com/repos/Goldkelch/qik-vrt/git/commits/${expectedHead}`,
      "tree reobservation",
    );
    if (!commit.tree || commit.tree.sha !== expectedTree) throw new Error("PR tree drift");

    const reviews = await observeJson(
      `https://api.github.com/repos/Goldkelch/qik-vrt/pulls/${expectedPr}/reviews?per_page=100`,
      "review disposition reobservation",
    );
    const marker = `<!-- qikvrt-requested-review-executor:v1 head=${expectedHead} disposition=APPROVE -->`;
    const treeLine = `- exact tree: \`${expectedTree}\``;
    const delegatedApprove = reviews.some(review => {
      const body = review.body || "";
      return review.user?.login === "github-actions[bot]" &&
        ["COMMENTED", "APPROVED"].includes(review.state) &&
        body.includes(marker) &&
        body.includes(treeLine) &&
        body.includes("independent Code-Owner approval: **not implied**");
    });
    if (!delegatedApprove) {
      throw new Error("missing exact-head substantive APPROVE disposition");
    }

    const alreadyApproved = reviews.some(review =>
      review.user?.login === expectedOwner &&
      review.state === "APPROVED" &&
      review.commit_id === expectedHead,
    );
    if (alreadyApproved) {
      document.documentElement.dataset.qikvrtReviewEffect = "ALREADY_APPROVED_REOBSERVE_REQUIRED";
      return;
    }

    const reviewButton = await waitFor(
      () => document.querySelector('button[data-hotkey="v"]') ||
        byText("button,summary", /Review changes|Änderungen überprüfen/i),
      "review changes",
    );
    reviewButton.click();

    const approve = await waitFor(
      () => document.querySelector('input[name="pull_request_review[event]"][value="approve"]') ||
        [...document.querySelectorAll('input[type="radio"]')].find(el => {
          const label = el.closest("label") || document.querySelector(`label[for="${el.id}"]`);
          return label && /Approve|Genehmigen/i.test(label.textContent || "");
        }),
      "approve option",
    );
    approve.click();

    const form = approve.closest("form");
    const submit = await waitFor(
      () => form?.querySelector('button[type="submit"]') ||
        byText('button[type="submit"],button', /Submit review|Review abgeben|Überprüfung absenden/i),
      "submit review",
    );
    submit.click();
    sessionStorage.setItem(key, "submitted");
    document.documentElement.dataset.qikvrtReviewEffect = "SUBMITTED_REOBSERVE_REQUIRED";
  }

  run().catch(error => hold(error.message));
})();
