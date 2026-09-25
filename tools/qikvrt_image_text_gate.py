#!/usr/bin/env python3
from collections import Counter
import json
import pathlib
import sys
import unicodedata

def fail(msg):
    print('QIKVRT_IMAGE_TEXT_HOLD: ' + msg, file=sys.stderr)
    raise SystemExit(1)

if len(sys.argv) != 2:
    fail('usage: qikvrt_image_text_gate.py SPEC.json')

p = pathlib.Path(sys.argv[1])
data = json.loads(p.read_text(encoding='utf-8'))
if data.get('schema') != 'qikvrt_image_text_fidelity_v1':
    fail('unexpected schema')

required = data.get('required_literals')
observed = data.get('observed_literals')
unexpected = data.get('unexpected_visible_text')
if not isinstance(required, list) or not required or not all(isinstance(x, str) and x for x in required):
    fail('required_literals must be a non-empty list of non-empty strings')
if not isinstance(observed, list) or not all(isinstance(x, str) for x in observed):
    fail('observed_literals must be strings')
if not isinstance(unexpected, list) or not all(isinstance(x, str) and x for x in unexpected):
    fail('unexpected_visible_text must contain only non-empty strings')

norm = lambda s: unicodedata.normalize('NFC', s)
req = [norm(x) for x in required]
obs = [norm(x) for x in observed]

req_counts = Counter(req)
obs_counts = Counter(obs)
if req_counts != obs_counts:
    missing = list((req_counts - obs_counts).elements())
    extra = list((obs_counts - req_counts).elements())
    fail('rendered literal multiset mismatch: missing=' + repr(missing) + ' extra=' + repr(extra))
if unexpected:
    fail('unexpected visible text: ' + repr(unexpected))
if data.get('human_visual_readback_complete') is not True:
    fail('human_visual_readback_complete is not true')
if data.get('spelling_review_complete') is not True:
    fail('spelling_review_complete is not true')
if data.get('accepted') is not True:
    fail('accepted is not true')

print('QIKVRT_IMAGE_TEXT_PASS')
