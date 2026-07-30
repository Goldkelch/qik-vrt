#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Read-only, fail-closed inventory probe for the remaining Zenodo subjects.

The probe verifies every record and public file against repository-bound exact
size/MD5/SHA-256 evidence. Identical payloads are inspected once. ZIPs are
recursively checked without extracting to the runner filesystem. Third-party
and cache trees are counted separately from first-party text assertion sources.
No Zenodo mutation or completion status is authorized by this tool.
"""
from __future__ import annotations
import argparse,base64,hashlib,io,json,pathlib,stat,time,urllib.error,urllib.parse,urllib.request,zipfile
from collections import Counter
from typing import Any,Mapping
SUBJECTS=[
 {'subject_id':'SUBJECT-b4849e1a2d6b2270','records':[
  {'id':21244412,'doi':'10.5281/zenodo.21244412','name':'ingolf-lohmann/qik-vrt-qikvrt-v13.164-28434-5434.zip'},
  {'id':21245282,'doi':'10.5281/zenodo.21245282','name':'ingolf-lohmann/qik-vrt-qikvrt-v13.164-1077-22520.zip'},
  {'id':21245951,'doi':'10.5281/zenodo.21245951','name':'ingolf-lohmann/qik-vrt-qikvrt-v13.164-9927-19949.zip'},
  {'id':21247297,'doi':'10.5281/zenodo.21247297','name':'ingolf-lohmann/qik-vrt-qikvrt-v13.164-32156-13407.zip'},
  {'id':21247388,'doi':'10.5281/zenodo.21247388','name':'ingolf-lohmann/qik-vrt-qikvrt-v13.164-1210-14474.zip'}],
  'file':{'bytes':150800,'md5':'57c0e108f240f54f4478c048f9ba958b','sha256':'ab68267007a75b58980acd23a6dea4e007de78ef044529cb70918a080d61bea0'}},
 {'subject_id':'SUBJECT-7956d8acdc473825','records':[{'id':21252415,'doi':'10.5281/zenodo.21252415','name':'ingolf-lohmann/qik-vrt-v2.13.4-node.zip'}],'file':{'bytes':300638,'md5':'8393efa42dbf53022f861bf993ca07e9','sha256':'e5194f4e28cda059979ff17b8d47494162cb9434b7b12f419fe2e200859165fa'}},
 {'subject_id':'SUBJECT-ce2390f18618ad0c','records':[{'id':21252649,'doi':'10.5281/zenodo.21252649','name':'ingolf-lohmann/qik-vrt-v2.13.4-node-r.zip'}],'file':{'bytes':305905,'md5':'6c3ad9e502cc56e7dea60a06bd01d3f7','sha256':'a773c71d99b912769c4b614fa0e430813d70b6d33683936c7b790e5985307df2'}},
 {'subject_id':'SUBJECT-780b9bf86425cee3','records':[{'id':21266670,'doi':'10.5281/zenodo.21266670','name':'ingolf-lohmann/qik-vrt-v2.13.4au1-node-productization.zip'}],'file':{'bytes':75863605,'md5':'1bc5307de317cd33409b59a7c424e1fc','sha256':'c5ff47f0a7873d9b38ea7ec7bd8da6a8903b4d6013d990cb08135185f69dcafc'}},
 {'subject_id':'SUBJECT-7fdb36aa7c07c07d','records':[{'id':21267021,'doi':'10.5281/zenodo.21267021','name':'ingolf-lohmann/qik-vrt-v2.13.4av1-node-open-multi-node.zip'}],'file':{'bytes':75962793,'md5':'ed4a71499081950a2e04afc089b6a1fe','sha256':'34d396667bf075ec9d2d87f8cd74b442ffa47537c4001fdbd8aa0ee319111244'}},
]
MAX_PUBLIC=128*1024*1024;MAX_DEPTH=8;MAX_ENTRIES=120000;MAX_ENTRY=768*1024*1024;MAX_TOTAL=4*1024*1024*1024;MAX_RATIO=4000.0;MAX_RETAIN=2*1024*1024
TEXT_EXT={'.c','.h','.cc','.cpp','.hpp','.py','.ps1','.sh','.bat','.cmd','.md','.txt','.json','.jsonl','.yaml','.yml','.toml','.ini','.cfg','.conf','.csv','.tsv','.xml','.html','.htm','.css','.js','.mjs','.cjs','.ts','.tsx','.jsx','.tex','.bib','.lean','.lake','.sha256','.sha512','.sum','.license','.notice','.gitignore','.gitattributes','.cff'}
TEXT_NAMES={'readme','license','notice','copying','copyright','makefile','dockerfile','ai','authors','changelog','changes','package.json','package-lock.json'}
THIRD={'node_modules','vendor','third_party','third-party','.venv','venv','site-packages','dist-info','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','.cache','.git','coverage','target'}
class E(RuntimeError):pass
def fail(x:str):raise E(x)
def dig(b:bytes):return {'bytes':len(b),'md5':hashlib.md5(b,usedforsecurity=False).hexdigest(),'sha256':hashlib.sha256(b).hexdigest(),'git_blob_sha1':hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()}
def get(url:str,accept:str,limit:int)->bytes:
 last=None
 for n in range(5):
  try:
   req=urllib.request.Request(url,headers={'Accept':accept,'User-Agent':'qikvrt-batch003-remaining-read-only-probe/1.0'})
   with urllib.request.urlopen(req,timeout=240) as r:
    u=urllib.parse.urlsplit(r.geturl());host=(u.hostname or '').lower()
    if u.scheme!='https' or not(host=='zenodo.org' or host.endswith('.zenodo.org')):fail(f'redirect outside Zenodo: {r.geturl()}')
    out=bytearray()
    while True:
     chunk=r.read(min(1024*1024,limit+1-len(out)))
     if not chunk:break
     out.extend(chunk)
     if len(out)>limit:fail(f'download bound exceeded: {url}')
    return bytes(out)
  except (urllib.error.URLError,TimeoutError,OSError) as ex:last=ex;time.sleep(2**n)
 raise E(f'GET failed {url}: {last}')
def files(v:Mapping[str,Any])->list[dict[str,Any]]:
 raw=v.get('files')
 if isinstance(raw,list):return [dict(x) for x in raw if isinstance(x,Mapping)]
 if isinstance(raw,Mapping):
  ent=raw.get('entries') if isinstance(raw.get('entries'),Mapping) else raw
  return [{**dict(x),'key':k} for k,x in ent.items() if isinstance(x,Mapping)]
 return []
def decode(b:bytes):
 if b'\0' in b[:4096] and not b.startswith((b'\xff\xfe',b'\xfe\xff')):return None,None
 for enc in ('utf-8-sig','utf-8','utf-16','cp1252'):
  try:t=b.decode(enc)
  except UnicodeDecodeError:continue
  if '\0' not in t:return t.replace('\r\n','\n').replace('\r','\n'),enc
 return None,None
def safe_path(name:str):
 if not name or '\\' in name or '\0' in name:fail(f'unsafe ZIP path encoding: {name!r}')
 p=pathlib.PurePosixPath(name)
 if p.is_absolute() or any(x in ('','.','..') for x in p.parts):fail(f'unsafe ZIP path: {name}')
 if len(p.as_posix())>1024:fail(f'ZIP path too long: {name}')
 return p
def third(path:pathlib.PurePosixPath):return any(x.casefold() in THIRD for x in path.parts)
def text_candidate(p:pathlib.PurePosixPath):return p.suffix.lower() in TEXT_EXT or p.name.lower() in TEXT_NAMES
def scalar_count(v:Any)->int:
 if isinstance(v,Mapping):return sum(scalar_count(x) for x in v.values()) or 1
 if isinstance(v,list):return sum(scalar_count(x) for x in v) or 1
 return 1
def inspect_zip(data:bytes,label:str,depth:int,state:dict[str,int],rows:list[dict[str,Any]]):
 if depth>MAX_DEPTH:fail(f'nested depth exceeds {MAX_DEPTH}: {label}')
 try:z=zipfile.ZipFile(io.BytesIO(data),'r')
 except zipfile.BadZipFile as ex:raise E(f'invalid ZIP {label}: {ex}') from ex
 with z:
  infos=z.infolist();state['entries']+=len(infos)
  if state['entries']>MAX_ENTRIES:fail('recursive entry bound exceeded')
  bad=z.testzip()
  if bad:fail(f'CRC failure {label}!/{bad}')
  seen=set();fold=set()
  for info in infos:
   p=safe_path(info.filename);n=p.as_posix().rstrip('/');f=n.casefold()
   if n in seen or f in fold:fail(f'duplicate/case collision: {label}!/{n}')
   seen.add(n);fold.add(f);mode=(info.external_attr>>16)&0xffff
   if mode and stat.S_ISLNK(mode):fail(f'symlink rejected: {label}!/{n}')
   if info.flag_bits&1:fail(f'encrypted entry rejected: {label}!/{n}')
   if info.file_size>MAX_ENTRY:fail(f'entry size bound: {label}!/{n}')
   state['bytes']+=info.file_size
   if state['bytes']>MAX_TOTAL:fail('recursive uncompressed byte bound exceeded')
   ratio=(float('inf') if info.file_size else 1.0) if info.compress_size==0 else info.file_size/info.compress_size
   if ratio>MAX_RATIO:fail(f'compression ratio bound: {label}!/{n}')
   q=f'{label}!/{n}';row={'qualified_path':q,'archive_depth':depth,'is_directory':info.is_dir(),'compressed_bytes':info.compress_size,'uncompressed_bytes':info.file_size,'third_party_or_cache':third(p)}
   if info.is_dir():row['content_class']='DIRECTORY';rows.append(row);continue
   b=z.read(info);row.update(dig(b));nested=(p.suffix.lower()=='.zip' or b.startswith(b'PK\x03\x04'))
   if nested:
    if not zipfile.is_zipfile(io.BytesIO(b)):fail(f'ZIP-labelled invalid payload: {q}')
    row['content_class']='NESTED_ZIP';rows.append(row);inspect_zip(b,q,depth+1,state,rows);continue
   t,enc=decode(b) if text_candidate(p) else (None,None)
   if t is None:row['content_class']='BINARY_OR_UNDECODED';rows.append(row);continue
   row['content_class']='TEXT';row['encoding']=enc;row['line_count']=len(t.splitlines());row['nonempty_line_count']=sum(bool(x.strip()) for x in t.splitlines())
   if p.suffix.lower()=='.json':
    try:row['json_scalar_count']=scalar_count(json.loads(t));row['json_valid']=True
    except json.JSONDecodeError:row['json_scalar_count']=0;row['json_valid']=False
   else:row['json_scalar_count']=0;row['json_valid']=None
   if not row['third_party_or_cache'] and len(b)<=MAX_RETAIN:row['text_utf8_base64']=base64.b64encode(t.encode()).decode()
   rows.append(row)
def record(subject:Mapping[str,Any],rec:Mapping[str,Any],cache:dict[str,dict[str,Any]]):
 rid=rec['id'];raw=get(f'https://zenodo.org/api/records/{rid}','application/json',8*1024*1024)
 try:v=json.loads(raw)
 except Exception as ex:raise E(f'invalid record JSON {rid}: {ex}') from ex
 if int(v.get('id') or 0)!=rid:fail(f'record identity drift: {rid}')
 doi=v.get('doi') or ((v.get('pids') or {}).get('doi') or {}).get('identifier')
 if doi not in (None,rec['doi']):fail(f'DOI drift {rid}: {doi}')
 fs=files(v);by={str(x.get('key') or x.get('filename') or x.get('name')):x for x in fs}
 if set(by)!={rec['name']}:fail(f'public file-set drift {rid}: {sorted(by)}')
 meta=by[rec['name']];exp=subject['file']
 if meta.get('size') is not None and int(meta['size'])!=exp['bytes']:fail(f'metadata size drift {rid}')
 cs=str(meta.get('checksum') or '').removeprefix('md5:')
 if cs and cs!=exp['md5']:fail(f'metadata md5 drift {rid}')
 links=meta.get('links') if isinstance(meta.get('links'),Mapping) else {};url=links.get('content') or links.get('download') or links.get('self')
 if not isinstance(url,str):url=f'https://zenodo.org/api/records/{rid}/files/{urllib.parse.quote(rec["name"],safe="")}/content'
 b=get(url,'application/octet-stream, */*;q=0.1',MAX_PUBLIC);d=dig(b)
 for k in ('bytes','md5','sha256'):
  if d[k]!=exp[k]:fail(f'exact public byte mismatch {rid}:{k}')
 if d['sha256'] not in cache:
  rows=[];state={'entries':0,'bytes':0};inspect_zip(b,rec['name'],0,state,rows);cache[d['sha256']]={'rows':rows,'state':state}
 return {'record_id':rid,'doi':rec['doi'],'public_name':rec['name'],**d,'payload_inventory_sha256':hashlib.sha256(json.dumps(cache[d['sha256']]['rows'],sort_keys=True,separators=(',',':')).encode()).hexdigest()}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=pathlib.Path,required=True);a=ap.parse_args();cache={};subs=[]
 for s in SUBJECTS:
  obs=[record(s,r,cache) for r in s['records']];payload=cache[s['file']['sha256']];rows=payload['rows'];c=Counter(x['content_class'] for x in rows);first=[x for x in rows if x['content_class']=='TEXT' and not x['third_party_or_cache']];thirdrows=[x for x in rows if x.get('third_party_or_cache')]
  subs.append({'subject_id':s['subject_id'],'record_observations':obs,'record_count':len(obs),'byte_identical_records':len({x['sha256'] for x in obs})==1,'payload_sha256':s['file']['sha256'],'recursive_summary':{'entry_count':len(rows),'maximum_depth':max((x['archive_depth'] for x in rows),default=0),'total_recursive_uncompressed_bytes':payload['state']['bytes'],'content_class_counts':dict(sorted(c.items())),'first_party_text_file_count':len(first),'first_party_nonempty_line_count':sum(x['nonempty_line_count'] for x in first),'first_party_json_scalar_count':sum(x['json_scalar_count'] for x in first),'third_party_or_cache_entry_count':len(thirdrows),'retained_first_party_text_file_count':sum('text_utf8_base64' in x for x in first)},'first_party_text_entries':first,'all_entries':rows})
 out={'_license':{'classification':'machine_readable_read_only_remaining_archive_probe','copyright':'Copyright 2026 Ingolf Lohmann','license':'CC-BY-NC-ND-4.0','rights_holder':'Ingolf Lohmann'},'schema':'qikvrt_batch003_remaining_archive_probe_v1','subjects':subs,'subject_count':len(subs),'safety_policy':{'absolute_paths_rejected':True,'backslashes_rejected':True,'casefold_collisions_rejected':True,'crc_verified':True,'decompression_bounds_enforced':True,'duplicates_rejected':True,'encrypted_entries_rejected':True,'nested_archives_recursively_checked':True,'symlinks_rejected':True,'traversal_rejected':True},'completion_claims':{'all_remaining_public_bytes_recovered':True,'all_remaining_archives_recursively_inspected':True,'all_remaining_claims_dispositioned':False,'proof_corpus_built':False,'proof_corpus_published_on_zenodo':False,'zenodo_mutation_authorized':False,'pass':False,'final_pass':False,'effect_ack_done':False}}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8',newline='\n')
 summary={'schema':'qikvrt_batch003_remaining_archive_probe_summary_v1','subjects':[{'subject_id':x['subject_id'],**x['recursive_summary'],'record_count':x['record_count'],'payload_sha256':x['payload_sha256']} for x in subs],'completion_claims':out['completion_claims']};sp=a.output.with_name('SUMMARY.json');sp.write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
 print(json.dumps(summary,sort_keys=True));print('PASS=false\nFINAL_PASS=false\nEFFECT_ACK_DONE=false\nZENODO_MUTATION=false')
if __name__=='__main__':
 try:main()
 except (E,OSError,UnicodeError,ValueError) as ex:print(f'BLOCK: {ex}');raise SystemExit(2)
