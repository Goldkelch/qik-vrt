<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Contributions and licensing

QIK-VRT does not accept code or documentation contributions for incorporation
merely because they were submitted through an issue, pull request, message, or
other repository channel.

Before a contribution can be merged, every contributor must identify the
work's authorship and third-party provenance and execute separate written
contribution terms acceptable to the project rights holder. Those terms must
authorize publication under `PolyForm-Noncommercial-1.0.0` and must expressly
address the project rights holder's ability to offer separate commercial
licenses. A Developer Certificate of Origin alone is not treated as that
commercial relicensing permission.

Unsolicited submissions remain the submitter's responsibility and create no
presumption of acceptance, assignment, confidentiality, or commercial license.
Third-party material must keep its original license and attribution.

## Before proposing a change

1. Identify the exact current file, behavior, or claim boundary involved.
2. For a software defect, record the full commit SHA, minimal sanitized input,
   expected result, observed result, and possible downstream effect.
3. Run the no-network demonstration when relevant:

   ```bash
   python3 examples/effect_haltpoint_demo.py
   ```

4. Run the complete verification gate:

   ```bash
   make test
   ```

5. Separate observation, inference, hypothesis, formal derivation, executable
   behavior, and empirical claim. Include primary sources or reproducible
   evidence for the exact level under review.
6. Do not include credentials, personal data, confidential material, or
   non-public vulnerability details. Follow `SECURITY.md` for security reports.

Issues may be used to establish whether a change should be explored. A pull
request is appropriate only after its scope and provenance are clear. Neither
an issue nor a pull request overrides the separate written contribution terms
required above.
