# QIK-VRT Mesh Fan-Out / Lossless Consolidation Benchmark

Source HEAD: 09a248f0f1743afe668d329faaaa6e051c24e578
Source TREE: 3649722bcbc536b39f257843c88f2269752801ca

| Fan-out | Median verified msg/s | Ratio vs 1 | Median latency ms | Median p95 ms | Consolidation ms | Lossless |
| ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| 1 | 52.612 | 1.000x | 17.365 | 30.032 | 0.220 | YES |
| 2 | 66.209 | 1.258x | 27.724 | 39.713 | 0.229 | YES |
| 4 | 71.480 | 1.359x | 53.163 | 69.267 | 0.216 | YES |
| 8 | 22.743 | 0.432x | 280.055 | 448.193 | 0.214 | YES |
| 16 | 46.042 | 0.875x | 259.490 | 409.755 | 0.227 | YES |

Every timed result was reobserved from all node-local ledgers before bounded Effect-Ack closure.
The consolidation gate requires exact cardinality, unique message IDs and preserved SHA-256 bindings.

Evidence boundary: hosted-runner loopback-TCP software benchmark only; no physical MC68000, FPGA, ASIC or silicon speedup and no patentability conclusion.
