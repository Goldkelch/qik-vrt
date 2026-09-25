#!/usr/bin/env python3
import argparse,json,pathlib,time,unicodedata,urllib.parse,urllib.request
API="https://zenodo.org/api/records"
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
def fetch_json(url,attempts=3,timeout=30):
 last=None
 for i in range(attempts):
  try:
   req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"qikvrt-zenodo-live-audit/1"})
   with urllib.request.urlopen(req,timeout=timeout) as r:return json.loads(r.read().decode())
  except Exception as exc:
   last=exc
   if i+1<attempts:time.sleep(2**i)
 raise RuntimeError(f"GET failed after {attempts} attempts: {url}: {last}")
def record_id(rec):
 try:return int(rec.get("id"))
 except Exception:return None
def search(query):
 url=API+"?"+urllib.parse.urlencode({"q":query,"size":100});out=[];seen=set();pages=0
 while url and pages<20:
  pages+=1;data=fetch_json(url)
  for rec in ((data.get("hits") or {}).get("hits") or []):
   rid=record_id(rec)
   if rid is not None and rid not in seen and creator_matches(rec):seen.add(rid);out.append(rec)
  nxt=(data.get("links") or {}).get("next");url=nxt if isinstance(nxt,str) and nxt else None
 return out
def classify(expected,verified,discovered,mismatches,errors):
 missing=sorted(set(expected)-set(verified));new=sorted(set(discovered)-set(expected))
 state="LIVE_READBACK_ERROR" if errors else "CREATOR_BINDING_MISMATCH" if mismatches else "EXPECTED_RECORD_MISSING" if missing else "SUCCESSOR_REQUIRED_NEW_PUBLIC_RECORDS" if new else "LIVE_READBACK_MATCH"
 return state,missing,new
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--snapshot",required=True);ap.add_argument("--output",required=True);a=ap.parse_args()
 snap=json.loads(pathlib.Path(a.snapshot).read_text());expected=sorted(int(x["record_id"]) for x in snap["records"]);verified=[];mismatches=[];errors=[]
 for rid in expected:
  try:
   rec=fetch_json(f"{API}/{rid}");(verified if creator_matches(rec) else mismatches).append(rid)
  except Exception as exc:errors.append({"record_id":rid,"error":str(exc)})
 discovered=set()
 for q in ('"Ingolf Lohmann"','"Lohmann, Ingolf"'):
  try:
   for rec in search(q):discovered.add(record_id(rec))
  except Exception as exc:errors.append({"search_query":q,"error":str(exc)})
 discovered.discard(None);state,missing,new=classify(expected,verified,sorted(discovered),mismatches,errors)
 result={"schema":"qikvrt_zenodo_personal_live_audit_v1","state":state,"expected_count":len(expected),"verified_expected_count":len(verified),"expected_record_ids":expected,"discovered_matching_record_ids":sorted(discovered),"new_record_ids":new,"missing_expected_record_ids":missing,"creator_mismatch_record_ids":sorted(mismatches),"errors":errors,"mutation":"NONE","predecessor_evidence_transfer":False}
 pathlib.Path(a.output).write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n");print(json.dumps(result,ensure_ascii=False,sort_keys=True));return 0 if state=="LIVE_READBACK_MATCH" else 2
if __name__=="__main__":raise SystemExit(main())
