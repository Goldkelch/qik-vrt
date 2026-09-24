#!/usr/bin/env python3
import json, pathlib, subprocess, tempfile

ROOT=pathlib.Path(__file__).resolve().parents[1]
gate=ROOT/'tools/qikvrt_image_text_gate.py'

def run(spec):
    with tempfile.NamedTemporaryFile('w',suffix='.json',encoding='utf-8',delete=False) as f:
        json.dump(spec,f)
        name=f.name
    return subprocess.run(['python3',str(gate),name],capture_output=True,text=True)

base={
 'schema':'qikvrt_image_text_fidelity_v1',
 'required_literals':['Bewusstsein ist Wechselwirkung!','EFFECT_ACK','EFFECT_ACK_DONE','q.e.d.','Ingolf Lohmann'],
 'observed_literals':['Bewusstsein ist Wechselwirkung!','EFFECT_ACK','EFFECT_ACK_DONE','q.e.d.','Ingolf Lohmann'],
 'unexpected_visible_text':[],
 'human_visual_readback_complete':True,
 'spelling_review_complete':True,
 'accepted':True
}
assert run(base).returncode==0
bad=dict(base); bad['observed_literals']=['Bewusstsein ist Wechselwirkung!','Effect_Ack','EFFECT_ACK_DONE','q.e.d.','Ingolf Lohmann']
assert run(bad).returncode!=0
extra=dict(base); extra['unexpected_visible_text']=['invented caption']
assert run(extra).returncode!=0
unchecked=dict(base); unchecked['spelling_review_complete']=False
assert run(unchecked).returncode!=0
print('PASS image text fidelity gate tests')
