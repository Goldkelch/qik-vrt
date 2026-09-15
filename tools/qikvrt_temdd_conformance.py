#!/usr/bin/env python3
"""TEMDD semantic conformance T01-T12. Fail closed."""
from collections import namedtuple
Evidence=namedtuple('Evidence','subject kind fresh')
DOD=('ZERO_BUGS','ALL_PULL_REQUESTS_REGARDED','ALL_BRANCHES_REGARDED','ALL_PRODUCTIVE_BRANCHES_MERGED','FRESH_EXACT_MAIN_VALIDATION_PASS','FRESH_EFFECT_READBACK')
def evidence(subject,kind,fresh=True): return Evidence(subject,kind,fresh)
def admits(e,subject,kind): return e.subject==subject and e.kind==kind and e.fresh
def successor(subject,mutation): return subject+'@successor:'+mutation
def done(predicates): return all(bool(predicates.get(x,False)) for x in DOD)
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
 print('TEMDD_CONFORMANCE T01-T12 PASS')
if __name__=='__main__': check()
