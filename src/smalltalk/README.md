# QIK-VRT Smalltalk core

`QikvrtEffectAck.st` is an independently executable Pharo Smalltalk implementation
of the C90 verified-snapshot kernel. Python remains the rich evidence/protocol
adapter; C90 remains the dependency-minimal kernel. Existing Python functionality
and tests are retained.

The 19 Boolean fields and five decisions share the existing C90 test-mask order.
All 2,621,440 combinations are compared byte-for-byte with the compiled C90
kernel, whose existing suite independently checks 7,864,387 assertions. The
Smalltalk test also rejects malformed snapshots and restores a freshly built
image before testing. These counts refer to the stated domains, not to millions
of independent end-to-end boot tests.

Another 23 representable boundary cases compare the rich Python engine with
the C90/Smalltalk results. Projection into the verified snapshot preserves
Python's reception rule: without a transport acknowledgement, a raw identifier
string is not an available effect-checkable input identity. This is a scoped
adapter check, not a claim that every Python protocol feature was ported.

```
python3 -B tools/qikvrt_smalltalk.py install
make smalltalk-test
python3 -B tools/qikvrt_smalltalk.py build --output /tmp/qikvrt-smalltalk-image
```

Source is stored in Git as standard Smalltalk file-in text. The generated image
is a derivative, not an editable source of authority. Each build begins with the
locked upstream image and records the exact source, image and lock hashes. The
Linux x86_64 VM and image archives are bound in `pharo-13.lock.json`; a changed
upstream URL response fails closed. Rollback deletes only an incomplete new
installation and never replaces a verified cache. A successful restore does not
approve, publish, deploy or complete the broader project.

The C enum and the Transputer D4 encoding are deliberately different:

| State | C90 enum | D4 wire |
| --- | ---: | ---: |
| EFFECT_NACK | 0 | 0 |
| EFFECT_ACK_CONTINUE | 1 | 1 |
| EFFECT_ACK_DONE | 2 | 4 |
| EFFECT_ACK_ISOLATE | 3 | 2 |
| EFFECT_ACK_BLOCK | 4 | 3 |

Use `wireCodeFor:` at the transport boundary; never send a C enum as D4 directly.

Upstream: [Pharo download](https://pharo.org/download),
[Pharo source](https://github.com/pharo-project/pharo),
[VM source](https://github.com/pharo-project/pharo-vm).
The upstream licenses are retained under `runtime/toolchains/pharo-*-LICENSE.txt`.
