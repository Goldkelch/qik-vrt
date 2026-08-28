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

  // DOM controls are observed from browser mutation edges, never by repeatedly
  // querying the page on a timer.  The one-shot AbortSignal timeout is a
  // fail-closed bound for an absent control, not a retry mechanism.
  function observeControl(getNode, description, timeoutMs = 5000) {
    const available = getNode();
    if (available) return Promise.resolve(available);
    if (typeof MutationObserver !== "function" ||
        typeof AbortSignal === "undefined" ||
        typeof AbortSignal.timeout !== "function") {
      return Promise.reject(new Error("event-driven DOM observation unavailable"));
    }
    const root = document.documentElement;
    if (!root) return Promise.reject(new Error("document root unavailable"));

    return new Promise((resolve, reject) => {
      const timeout = AbortSignal.timeout(timeoutMs);
      let settled = false;
      let observer;
      const finish = callback => {
        if (settled) return;
        settled = true;
        observer.disconnect();
        timeout.removeEventListener("abort", onTimeout);
        callback();
      };
      const onTimeout = () =>
        finish(() => reject(new Error(`missing control: ${description}`)));
      const onMutation = () => {
        const node = getNode();
        if (node) finish(() => resolve(node));
      };

      observer = new MutationObserver(onMutation);
      observer.observe(root, {attributes: true, childList: true, subtree: true});
      timeout.addEventListener("abort", onTimeout, {once: true});
      if (timeout.aborted) onTimeout();
      else onMutation();
    });
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

    const reviewButton = await observeControl(
      () => document.querySelector('button[data-hotkey="v"]') ||
        byText("button,summary", /Review changes|Änderungen überprüfen/i),
      "review changes",
    );
    reviewButton.click();

    const approve = await observeControl(
      () => document.querySelector('input[name="pull_request_review[event]"][value="approve"]') ||
        [...document.querySelectorAll('input[type="radio"]')].find(el => {
          const label = el.closest("label") || document.querySelector(`label[for="${el.id}"]`);
          return label && /Approve|Genehmigen/i.test(label.textContent || "");
        }),
      "approve option",
    );
    approve.click();

    const form = approve.closest("form");
    const submit = await observeControl(
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
