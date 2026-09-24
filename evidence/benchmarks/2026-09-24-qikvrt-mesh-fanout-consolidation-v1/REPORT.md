# QIK-VRT Mesh Fan-Out / Lossless Consolidation Benchmark

Source HEAD: 9369e7c486fcbf8eff295ad512e0df05f8705c5f
Source TREE: fd2eee9b83f41376be44eb5e81d2935e67becaca

| Fan-out | Median verified msg/s | Ratio vs 1 | Median latency ms | Median p95 ms | Consolidation ms | Lossless |
| ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| 1 | 70.282 | 1.000x | 13.907 | 18.586 | 0.162 | YES |
| 2 | 0.000 | 0.000x | 0.000 | 0.000 | 0.050 | NO |
| 4 | 0.000 | 0.000x | 0.000 | 0.000 | 0.042 | NO |
| 8 | 0.000 | 0.000x | 0.000 | 0.000 | 0.045 | NO |
| 16 | 0.000 | 0.000x | 0.000 | 0.000 | 0.045 | NO |

Every timed result was reobserved from all node-local ledgers before bounded Effect-Ack closure.
The consolidation gate requires exact cardinality, unique message IDs and preserved SHA-256 bindings.

Evidence boundary: hosted-runner loopback-TCP software benchmark only; no physical MC68000, FPGA, ASIC or silicon speedup and no patentability conclusion.
