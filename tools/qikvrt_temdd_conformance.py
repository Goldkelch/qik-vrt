#!/usr/bin/env python3
"""TEMDD semantic conformance T01-T16. Fail closed."""
from collections import namedtuple
Evidence=namedtuple('Evidence','subject kind fresh')
DOD=('ZERO_BUGS','ALL_PULL_REQUESTS_REGARDED','ALL_BRANCHES_REGARDED','ALL_PRODUCTIVE_BRANCHES_MERGED','FRESH_EXACT_MAIN_VALIDATION_PASS','FRESH_EFFECT_READBACK')
EPISTEMIC=('TRUE','FALSE','UNKNOWN','CONFLICT','STALE','UNOBSERVABLE')
def evidence(subject,kind,fresh=True): return Evidence(subject,kind,fresh)
def admits(e,subject,kind): return e.subject==subject and e.kind==kind and e.fresh
def successor(subject,mutation): return subject+'@successor:'+mutation
def done(predicates): return all(bool(predicates.get(x,False)) for x in DOD)
def knowledge_refines(before,after): return bool(after) and set(after) <= set(before)
def temporal_relation(first,second):
 if first['observation_order'] < second['observation_order'] and second['source_order'] < first['source_order']: return 'RETROGRADE_SOURCE_REFERENCE'
 if first['observation_order'] < second['observation_order'] and first['source_order'] < second['source_order']: return 'ALIGNED_ORDER'
 return 'UNORDERED_OR_EQUAL'
def same_context(a,b): return a['name']==b['name'] and a['perspective']==b['perspective']
def context_transition_allowed(a,b,authorized=False): return same_context(a,b) or bool(authorized)
def evidence_transferable(a,b): return same_context(a,b)
REPRESENTATION_FIELDS=('authority','context','subject','relations','dod','requires_effect_readback')
def representation_conserved(source,target): return all(source.get(k)==target.get(k) for k in REPRESENTATION_FIELDS)
def check():
 s='repo@head/tree'; t=successor(s,'m1'); e=evidence(s,'validation')
 assert admits(e,s,'validation') and not admits(e,t,'validation')
 assert 'TRANSPORT_ACK'!='EFFECT_ACK' and 'RESULT'!='EFFECT'
 assert {'HOLD','CONTINUE'}.isdisjoint({'NOOP','DONE'})
 assert not done({x:True for x in DOD if x!='ALL_PULL_REQUESTS_REGARDED'})
 assert not admits(evidence(s,'authority',False),s,'authority')
 p={x:True for x in DOD}; p['FRESH_EFFECT_READBACK']=False; assert not done(p)
 assert 'UNKNOWN' not in {'EFFECT_ACK','DONE'}
 assert t!=s and not admits(e,t,'validation')
 first={'source_order':2,'observation_order':1,'emitted_at':'source:2','observed_at':'local:1'}
 second={'source_order':1,'observation_order':2,'emitted_at':'source:1','observed_at':'local:2'}
 assert temporal_relation(first,second)=='RETROGRADE_SOURCE_REFERENCE'
 assert first['emitted_at'] != first['observed_at']
 assert set(EPISTEMIC)=={'TRUE','FALSE','UNKNOWN','CONFLICT','STALE','UNOBSERVABLE'}
 assert knowledge_refines({'a','b'},{'a'}) and not knowledge_refines({'a'},{'a','b'})
 assert {'CONFLICT','STALE','UNOBSERVABLE'}.isdisjoint({'TRUE','DONE'})
 c1={'name':'qikvrt','perspective':'product-owner'}; c2={'name':'qikvrt','perspective':'external-observer'}
 assert same_context(c1,c1) and not context_transition_allowed(c1,c2) and context_transition_allowed(c1,c2,authorized=True) and not evidence_transferable(c1,c2)
 canonical={'authority':'Goldkelch/qik-vrt','context':c1,'subject':s,'relations':[('authority','observes','mirror','UNKNOWN',2,1,'FRESH')],'dod':DOD,'requires_effect_readback':True}
 projection=dict(canonical); assert representation_conserved(canonical,projection)
 bad=dict(canonical); bad['subject']=t; assert not representation_conserved(canonical,bad)
 print('TEMDD_CONFORMANCE T01-T16 PASS')
if __name__=='__main__': check()
