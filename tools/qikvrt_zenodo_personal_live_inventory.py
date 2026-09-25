#!/usr/bin/env python3
import argparse,json,os,pathlib,time,unicodedata,urllib.parse,urllib.request,urllib.error
BASE="https://zenodo.org"
PUBLIC_API=BASE+"/api/records"
OWNER_API=BASE+"/api/deposit/depositions"
PAGE_SIZE=100
MAX_PAGES=100

def norm(s):return "".join(c for c in unicodedata.normalize("NFKD",str(s)).lower() if c.isalnum())
def creator_names(rec):
 out=[]
 for c in ((rec.get("metadata") or {}).get("creators") or []):
  if isinstance(c,dict):
   p=c.get("person_or_org")
   if isinstance(p,dict) and p.get("name"):out.append(str(p["name"]))
   elif c.get("name"):out.append(str(c["name"]))
 return out
def creator_matches(rec):return any("ingolf" in norm(n) and "lohmann" in norm(n) for n in creator_names(rec))

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  return None

def fetch_json(url,token=None,attempts=3,timeout=30):
 last=None
 opener=urllib.request.build_opener(NoRedirect())
 for i in range(attempts):
  try:
   headers={"Accept":"application/json","User-Agent":"qikvrt-zenodo-live-audit/2"}
   if token:headers["Authorization"]="Bearer "+token
   req=urllib.request.Request(url,headers=headers,method="GET")
   with opener.open(req,timeout=timeout) as r:
    if r.geturl()!=url:raise RuntimeError("response URL drift")
    return json.loads(r.read().decode("utf-8"))
  except Exception as exc:
   last=exc
   if i+1<attempts:time.sleep(2**i)
 raise RuntimeError(f"GET failed after {attempts} attempts: {urllib.parse.urlsplit(url).path}: {type(last).__name__}")

def record_id(rec):
 try:return int(rec.get("id"))
 except Exception:return None

def deposition_record_id(dep):
 for key in ("record_id","id"):
  try:
   value=int(dep.get(key))
   if value>0:return value
  except Exception:pass
 return None

def deposition_is_published(dep):
 state=str(dep.get("state") or "").lower()
 return dep.get("submitted") is True or state in {"done","published"} or bool(dep.get("doi"))

def owner_inventory_pass(token):
 observed={}
 for page in range(1,MAX_PAGES+1):
  query=urllib.parse.urlencode({"page":page,"size":PAGE_SIZE})
  value=fetch_json(OWNER_API+"?"+query,token=token)
  if not isinstance(value,list) or not all(isinstance(x,dict) for x in value):
   raise RuntimeError("owner inventory page must be an array of objects")
  if len(value)>PAGE_SIZE:raise RuntimeError("owner inventory page-size bound exceeded")
  if not value:return [observed[k] for k in sorted(observed)]
  for dep in value:
   did=deposition_record_id(dep)
   if did is None:raise RuntimeError("owner deposition has no positive identity")
   if did in observed:raise RuntimeError("owner inventory repeated a deposition identity")
   observed[did]=dep
  if len(value)<PAGE_SIZE:return [observed[k] for k in sorted(observed)]
 raise RuntimeError("owner inventory exceeded bounded page count")

def stable_owner_inventory(token):
 first=owner_inventory_pass(token);second=owner_inventory_pass(token)
 a=json.dumps(first,ensure_ascii=False,sort_keys=True,separators=(",",":"))
 b=json.dumps(second,ensure_ascii=False,sort_keys=True,separators=(",",":"))
 if a!=b:raise RuntimeError("owner inventory changed between complete passes")
 return first

def classify(expected,verified,owner_published,mismatches,errors):
 missing_public=sorted(set(expected)-set(verified))
 missing_owner=sorted(set(expected)-set(owner_published))
 new=sorted(set(owner_published)-set(expected))
 if errors:state="LIVE_READBACK_ERROR"
 elif mismatches:state="CREATOR_BINDING_MISMATCH"
 elif missing_public:state="EXPECTED_PUBLIC_RECORD_MISSING"
 elif missing_owner:state="EXPECTED_RECORD_NOT_IN_OWNER_INVENTORY"
 elif new:state="SUCCESSOR_REQUIRED_NEW_PUBLIC_RECORDS"
 else:state="LIVE_READBACK_MATCH"
 return state,missing_public,missing_owner,new

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--snapshot",required=True);ap.add_argument("--output",required=True);a=ap.parse_args()
 token=os.environ.get("ZENODO_ACCESS_TOKEN","").strip()
 if not token:raise SystemExit("BLOCK: ZENODO_ACCESS_TOKEN unavailable")
 snap=json.loads(pathlib.Path(a.snapshot).read_text(encoding="utf-8"))
 expected=sorted(int(x["record_id"]) for x in snap["records"])
 verified=[];mismatches=[];errors=[]
 for rid in expected:
  try:
   rec=fetch_json(f"{PUBLIC_API}/{rid}")
   (verified if creator_matches(rec) else mismatches).append(rid)
  except Exception as exc:errors.append({"record_id":rid,"error":str(exc)})
 owner=[]
 try:owner=stable_owner_inventory(token)
 except Exception as exc:errors.append({"owner_inventory_error":str(exc)})
 owner_all=sorted(x for x in (deposition_record_id(d) for d in owner) if x is not None)
 owner_published=sorted(deposition_record_id(d) for d in owner if deposition_record_id(d) is not None and deposition_is_published(d))
 owner_unpublished=sorted(set(owner_all)-set(owner_published))
 state,missing_public,missing_owner,new=classify(expected,verified,owner_published,mismatches,errors)
 result={"schema":"qikvrt_zenodo_personal_live_audit_v2","state":state,"expected_count":len(expected),"verified_expected_count":len(verified),"expected_record_ids":expected,"owner_deposition_count":len(owner_all),"owner_published_record_ids":owner_published,"owner_unpublished_deposition_ids":owner_unpublished,"new_record_ids":new,"missing_expected_public_record_ids":missing_public,"missing_expected_owner_record_ids":missing_owner,"creator_mismatch_record_ids":sorted(mismatches),"errors":errors,"mutation":"NONE","owner_inventory_passes":2,"predecessor_evidence_transfer":False}
 pathlib.Path(a.output).write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(result,ensure_ascii=False,sort_keys=True))
 return 0 if state=="LIVE_READBACK_MATCH" else 2
if __name__=="__main__":raise SystemExit(main())
