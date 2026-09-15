#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import pathlib
import tempfile
import unittest
from types import SimpleNamespace

from tools import qikvrt_github_observe as observe


class GitHubObserveTests(unittest.TestCase):
    @staticmethod
    def completed(returncode: int, *, stdout: str = "", stderr: str = ""):
        return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)

    def test_successful_read_uses_only_the_exact_gh_api_command(self):
        commands = []

        def runner(command, **_kwargs):
            commands.append(command)
            return self.completed(0, stdout='{"sha":"a"}\n')

        result = observe.run_gh_api_read(
            ["repos/Goldkelch/qik-vrt/commits/main", "--jq", ".sha"],
            runner=runner,
            sleeper=self.fail,
        )

        self.assertEqual(result, '{"sha":"a"}\n')
        self.assertEqual(
            commands,
            [["gh", "api", "repos/Goldkelch/qik-vrt/commits/main", "--jq", ".sha"]],
        )

    def test_quota_read_retries_only_on_the_bounded_zero_fifteen_fortyfive_schedule(self):
        commands = []
        sleeps = []

        def runner(command, **_kwargs):
            commands.append(command)
            return self.completed(
                1,
                stderr="HTTP 403: API rate limit exceeded for installation.",
            )

        with self.assertRaises(observe.GitHubInstallationRateLimit) as raised:
            observe.run_gh_api_read(
                ["repos/Goldkelch/qik-vrt/commits/main"],
                runner=runner,
                sleeper=sleeps.append,
            )

        self.assertEqual(str(raised.exception), observe.GITHUB_INSTALLATION_RATE_LIMIT_BLOCKER)
        self.assertEqual(len(commands), 3)
        self.assertEqual(sleeps, [15, 45])

    def test_installation_id_quota_variant_uses_the_same_bounded_policy(self):
        commands = []

        def runner(command, **_kwargs):
            commands.append(command)
            return self.completed(
                1,
                stderr="HTTP 403: API rate limit exceeded for installation ID 12345.",
            )

        with self.assertRaises(observe.GitHubInstallationRateLimit):
            observe.run_gh_api_read(
                ["repos/Goldkelch/qik-vrt/commits/main"],
                runner=runner,
                sleeper=lambda _delay: None,
            )
        self.assertEqual(len(commands), 3)

    def test_nonquota_failure_is_never_retried(self):
        commands = []

        def runner(command, **_kwargs):
            commands.append(command)
            return self.completed(1, stderr="HTTP 404: Not Found")

        with self.assertRaisesRegex(observe.GitHubObservationError, "HTTP 404"):
            observe.run_gh_api_read(
                ["repos/Goldkelch/qik-vrt/commits/missing"],
                runner=runner,
                sleeper=self.fail,
            )
        self.assertEqual(len(commands), 1)

    def test_mutation_arguments_are_rejected_before_subprocess_execution(self):
        for arguments in (
            ["--method", "POST", "repos/Goldkelch/qik-vrt/dispatches"],
            ["--method=POST", "repos/Goldkelch/qik-vrt/dispatches"],
            ["-XPOST", "repos/Goldkelch/qik-vrt/dispatches"],
            ["--input=-", "repos/Goldkelch/qik-vrt/dispatches"],
            ["-fstate=success", "repos/Goldkelch/qik-vrt/statuses/main"],
        ):
            with self.subTest(arguments=arguments), self.assertRaisesRegex(
                observe.GitHubObservationError, "forbids mutation"
            ):
                observe.run_gh_api_read(
                    arguments,
                    runner=self.fail,
                    sleeper=self.fail,
                )

    def test_only_the_control_plane_read_option_grammar_is_admitted(self):
        self.assertEqual(
            observe._validate_read_arguments(
                ["--paginate", "--slurp", "repos/Goldkelch/qik-vrt/issues/1/comments", "--jq", ".[]"]
            ),
            ["--paginate", "--slurp", "repos/Goldkelch/qik-vrt/issues/1/comments", "--jq", ".[]"],
        )
        with self.assertRaisesRegex(observe.GitHubObservationError, "permits only"):
            observe._validate_read_arguments(["--hostname", "api.github.com", "repos/Goldkelch/qik-vrt"])

    def test_cli_reports_a_machine_readable_rate_limit_exit(self):
        original = observe.run_gh_api_read
        try:
            def exhausted(_arguments):
                raise observe.GitHubInstallationRateLimit(
                    observe.GITHUB_INSTALLATION_RATE_LIMIT_BLOCKER
                )

            observe.run_gh_api_read = exhausted
            self.assertEqual(observe.main(["repos/Goldkelch/qik-vrt/commits/main"]), 75)
        finally:
            observe.run_gh_api_read = original

    def test_binary_read_uses_the_same_read_only_quota_wrapper_and_atomic_destination(self):
        commands = []
        with tempfile.TemporaryDirectory() as directory:
            destination = pathlib.Path(directory) / "evidence.zip"

            def runner(command, **_kwargs):
                commands.append(command)
                pathlib.Path(command[3]).write_bytes(b"PK\x03\x04evidence")
                return self.completed(0)

            observe.run_gh_api_read_to_file(
                ["repos/Goldkelch/qik-vrt/actions/artifacts/7/zip"],
                destination,
                runner=runner,
                sleeper=self.fail,
            )

            self.assertEqual(destination.read_bytes(), b"PK\x03\x04evidence")
            self.assertEqual(
                commands[0][:4],
                ["gh", "api", "--output", commands[0][3]],
            )
            self.assertEqual(commands[0][4], "repos/Goldkelch/qik-vrt/actions/artifacts/7/zip")

    def test_binary_read_quota_is_typed_and_never_publishes_a_partial_file(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = pathlib.Path(directory) / "evidence.zip"

            def runner(_command, **_kwargs):
                return self.completed(
                    1,
                    stderr="HTTP 403: API rate limit exceeded for installation ID 12345.",
                )

            with self.assertRaises(observe.GitHubInstallationRateLimit):
                observe.run_gh_api_read_to_file(
                    ["repos/Goldkelch/qik-vrt/actions/artifacts/7/zip"],
                    destination,
                    runner=runner,
                    sleeper=lambda _delay: None,
                )
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
