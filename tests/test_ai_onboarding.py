# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import pathlib
import re
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
AI = ROOT / "AI"
FORM = ROOT / ".github/ISSUE_TEMPLATE/ai_onboarding.yml"
SCRIPT = ROOT / "scripts/init_working_memory.sh"


class AIOnboardingTests(unittest.TestCase):
    def test_root_entrypoint_has_exactly_three_questions(self) -> None:
        source = AI.read_text(encoding="utf-8")
        questions = re.findall(r"^QUESTION_[123]_[A-Z]+$", source, flags=re.MULTILINE)
        self.assertEqual(
            questions,
            [
                "QUESTION_1_PURPOSE",
                "QUESTION_2_RUNTIME",
                "QUESTION_3_PERSISTENCE",
            ],
        )
        self.assertNotRegex(source, r"^QUESTION_[4-9]_", msg="a fourth question is forbidden")
        self.assertIn("Default: experiments", source)
        self.assertIn("Default: cli", source)
        self.assertIn("Default: local", source)

    def test_root_entrypoint_emits_one_clone_fork_and_start_binding(self) -> None:
        source = AI.read_text(encoding="utf-8")
        template = source.split("FINAL_OUTPUT_TEMPLATE", 1)[1].split(
            "REPOSITORY EVIDENCE BOUNDARY", 1
        )[0]
        self.assertEqual(template.count("git clone https://github.com/Goldkelch/qik-vrt.git"), 1)
        self.assertEqual(template.count("https://github.com/Goldkelch/qik-vrt/fork"), 1)
        self.assertEqual(template.count("./scripts/init_working_memory.sh"), 1)

    def test_issue_form_contains_only_the_three_choice_fields(self) -> None:
        source = FORM.read_text(encoding="utf-8")
        self.assertEqual(source.count("  - type: dropdown\n"), 3)
        self.assertIn("id: purpose", source)
        self.assertIn("id: runtime", source)
        self.assertIn("id: persistence", source)

    def test_initializer_is_posix_parseable_and_effect_free(self) -> None:
        syntax = subprocess.run(
            ["sh", "-n", str(SCRIPT)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("Performs no network access", source)
        self.assertIn("QIKVRT_EXTERNAL_EFFECTS=disabled", source)

    def test_initializer_prints_bound_env_template(self) -> None:
        completed = subprocess.run(
            [
                str(SCRIPT),
                "--mode=proofs",
                "--runtime=lean4",
                "--backup=github",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("QIKVRT_WORKING_MEMORY_MODE=proofs", completed.stdout)
        self.assertIn("QIKVRT_WORKING_MEMORY_RUNTIME=lean4", completed.stdout)
        self.assertIn("QIKVRT_WORKING_MEMORY_BACKUP=github", completed.stdout)
        self.assertIn("QIKVRT_EXTERNAL_EFFECTS=disabled", completed.stdout)

    def test_initializer_fails_closed_on_invalid_choice(self) -> None:
        completed = subprocess.run(
            [
                str(SCRIPT),
                "--mode=unknown",
                "--runtime=cli",
                "--backup=local",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("QIKVRT_WORKING_MEMORY_BLOCK", completed.stderr)


if __name__ == "__main__":
    unittest.main()
