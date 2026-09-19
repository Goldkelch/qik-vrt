#!/usr/bin/env python3
"""Verify this exact essay's coverage and negative scope boundaries; no network or publication."""
import collections,copy,hashlib,json,pathlib
D=pathlib.Path(__file__).resolve().parent
S='01545bdd5714c32ca91928daea8aefb32a3ca2508fd1e850106c0a162a44a610'
B='26d8afb67477e0e5b4e793236963477171d3abef'
def check(raw,matrix,sources):
    assert len(raw)==13618 and hashlib.sha256(raw).hexdigest()==S,'ARTICLE_IDENTITY'
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==B,'ARTICLE_BLOB'
    lines=raw.decode('utf-8').splitlines()
    assert len(lines)==319,'LINE_COUNT'
    wanted={i for i,l in enumerate(lines,1) if l.strip()}
    claims=matrix['claims'];excluded=matrix['structural_lines']
    assigned=[c['line'] for c in claims]+[e['line'] for e in excluded]
    assert len(assigned)==len(set(assigned)) and set(assigned)==wanted,'FULL_COVERAGE'
    assert matrix['claim_count']==len(claims),'COUNT'
    assert len({c['claim_id'] for c in claims})==len(claims),'IDS'
    source_ids={s['source_id'] for s in sources['sources']}
    for c in claims:
        assert c['statement']==lines[c['line']-1],'EXACT_STATEMENT'
        assert hashlib.sha256(c['statement'].encode()).hexdigest()==c['line_sha256'],'LINE_DIGEST'
        assert c['classification'] in {'SOURCE_BOUND','INTERPRETATIVE','NORMATIVE'},'NO_UNBACKED_FORMAL_OR_EMPIRICAL'
        assert c['boundary'] and not c['proof_refs'],'SCOPE_NOT_THEOREM'
        assert set(c['sources'])<=source_ids,'REFERENCES'
        if c['classification']=='SOURCE_BOUND':assert c['sources'],'SOURCE_REQUIRED'
    by={c['line']:c for c in claims}
    for n in [29,31,99,113,129,131,173,205,207]:
        assert by[n]['classification']=='INTERPRETATIVE','BELIEF_NOT_PROOF'
    assert 'selbstauskunft' in by[75]['boundary'].lower() and 'nicht' in by[75]['boundary'],'BIOGRAPHY_SCOPE'
    x=next(s for s in sources['sources'] if s['source_id']=='XING_KARLSRUHE')
    assert x['profile_url']=='https://www.xing.com/profile/Ingolf_Lohmann2' and x['profile_body_obtained'] is False,'XING_BOUNDARY'
    assert sources['PREDECESSOR_EVIDENCE_TRANSFER'] is False,'NO_TRANSFER'
    return len(claims)
def run_tests():
    raw=(D/'Die_Wahrheit_braucht_keine_Verschwoerungstheorie.txt').read_bytes()
    m=json.loads((D/'CLAIM_MATRIX.json').read_text());s=json.loads((D/'SOURCE_BINDINGS.json').read_text())
    count=check(raw,m,s);results=[]
    def rejected(name,rr,mm,ss):
        try:check(rr,mm,ss)
        except (AssertionError,KeyError,StopIteration):results.append({'name':name,'result':'EXPECTED_REJECTION'});return
        raise AssertionError('negative fixture admitted: '+name)
    rejected('changed_article',raw+b' ',m,s)
    mm=copy.deepcopy(m);mm['claims'].pop();rejected('omitted_line',raw,mm,s)
    mm=copy.deepcopy(m);mm['claims'].append(copy.deepcopy(mm['claims'][0]));rejected('duplicate_claim',raw,mm,s)
    mm=copy.deepcopy(m);next(c for c in mm['claims'] if c['line']==99)['classification']='FORMAL_PROVED';rejected('benchmark_claim_laundered',raw,mm,s)
    mm=copy.deepcopy(m);next(c for c in mm['claims'] if c['line']==23)['sources']=['MISSING'];rejected('unresolved_source',raw,mm,s)
    ss=copy.deepcopy(s);ss['PREDECESSOR_EVIDENCE_TRANSFER']=True;rejected('predecessor_transfer',raw,m,ss)
    ss=copy.deepcopy(s);next(x for x in ss['sources'] if x['source_id']=='XING_KARLSRUHE')['profile_body_obtained']=True;rejected('invented_profile_read',raw,m,ss)
    mm=copy.deepcopy(m);next(c for c in mm['claims'] if c['line']==75)['boundary']='Arbeitgeberbestätigung';rejected('biography_overreach',raw,mm,s)
    return {'schema':'qikvrt_pr1128_scope_tests_v1','claim_count':count,'positive_fixture':'VERIFIED','negative_tests':results,'all_nonblank_lines_accounted':True,'article_sha256':S,'native_P3':False,'owner_upload_authorization':False,'ZENODO_PUBLICATION':False,'DONE':False,'scope':'identity and claim disposition, not natural-language truth or empirical superiority'}
if __name__=='__main__':print(json.dumps(run_tests(),ensure_ascii=False,sort_keys=True,indent=2))
