#!/usr/bin/env python3
import argparse,datetime,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def git(*a): return subprocess.check_output(['git',*a],cwd=ROOT,text=True).strip()
def event(sequence=1):
 head=git('rev-parse','HEAD'); tree=git('rev-parse','HEAD^{tree}')
 return {'sequence':sequence,'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z'),'repository':'Goldkelch/qik-vrt','head_sha':head,'tree_sha':tree,'kind':'repository.subject','state':'OBSERVED','subject':{'head_sha':head,'tree_sha':tree},'provenance':{'carrier':'repository-native-monitorhook-v1'},'validity':'CURRENT','receipts':[],'relations':[]}
def main():
 p=argparse.ArgumentParser();p.add_argument('--format',choices=['json','ndjson','sse'],default='json');p.add_argument('--sequence',type=int,default=1);a=p.parse_args();e=event(a.sequence)
 if a.format=='json': print(json.dumps({'schema':'QIKVRT_MONITORHOOK_V1','events':[e]},sort_keys=True))
 elif a.format=='ndjson': print(json.dumps(e,sort_keys=True))
 else: print('id: %s\nevent: %s\ndata: %s\n'%(e['sequence'],e['kind'],json.dumps(e,sort_keys=True)))
if __name__=='__main__': main()
