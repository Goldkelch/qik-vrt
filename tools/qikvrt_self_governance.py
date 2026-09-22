from __future__ import annotations
import json, os, urllib.request
from pathlib import Path
def fail(msg): raise SystemExit("BLOCK: "+msg)
p=json.loads(Path("policy/EXECUTABLE_ABSTRACTION_COMPLETION_V1.json").read_text())
target=p.get("repository_target_state") or fail("repository_target_state absent")
closure=p.get("repository_recursive_closure") or fail("repository_recursive_closure absent")
if target.get("self_observation",{}).get("required") is not True: fail("self observation not mandatory")
if closure.get("fixed_point")!="OPEN_ISSUES=0 AND OPEN_PULL_REQUESTS=0 AND UNMERGED_WORK_BRANCHES=0": fail("fixed point changed")
if closure.get("post_fixed_point")!="ENTER_CONTINUOUS_PERFORMANCE_OPTIMIZATION": fail("optimization transition changed")
if closure.get("release_policy",{}).get("release_does_not_stop_recursion") is not True: fail("release stops recursion")
readme=Path("README.md").read_text()
for n in ("OPEN_ISSUES = 0","OPEN_PULL_REQUESTS = 0","UNMERGED_WORK_BRANCHES = 0","MEASURE → IDENTIFY BOTTLENECK"):
    if n not in readme: fail("README target missing: "+n)
watch=Path(".github/workflows/qikvrt_reflexive_repository_watchdog.yml").read_text()
if "cancel-in-progress: false" not in watch or "cancel-in-progress: true" in watch: fail("watchdog preemptive")
if os.environ.get("QIKVRT_EVENT") in {"push","schedule","workflow_dispatch"}:
    repo=os.environ["QIKVRT_REPOSITORY"]; token=os.environ["GH_TOKEN"]
    def api(path):
        req=urllib.request.Request("https://api.github.com/repos/"+repo+path,headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","User-Agent":"qikvrt-self-governance"})
        with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
    items=api("/issues?state=open&per_page=100")
    issues=sum("pull_request" not in x for x in items); prs=sum("pull_request" in x for x in items)
    branches=api("/branches?per_page=100"); work=sum(x["name"]!="main" for x in branches)
    print(json.dumps({"state":"CONTINUE" if issues or prs or work else "REPOSITORY_WORK_FIXED_POINT","open_issues":issues,"open_pull_requests":prs,"non_main_branches":work},sort_keys=True))
print("SELF_GOVERNANCE_INVARIANTS=PASS")
