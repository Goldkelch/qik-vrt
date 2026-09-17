#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Run one read-only ``gh api`` observation with bounded quota recovery.

This is deliberately small enough to be used both by trusted-main workflow
heredocs and by shell steps.  It never accepts a mutation argument.  A shared
GitHub App installation quota is a D0=2 reobservation condition, not a reason
to retry a POST, PATCH or PUT.
"""
from __future__ import annotations

import subprocess
import sys
import time
import os
import pathlib
import tempfile
from collections.abc import Callable, Sequence
from typing import Any

GITHUB_INSTALLATION_RATE_LIMIT_MARKER = "API rate limit exceeded for installation"
GITHUB_INSTALLATION_RATE_LIMIT_BLOCKER = "GITHUB_INSTALLATION_RATE_LIMIT_EXHAUSTED"
GITHUB_READ_RATE_LIMIT_BACKOFF_SECONDS = (0, 15, 45)
RATE_LIMIT_EXIT_STATUS = 75
_MUTATION_ARGUMENTS = (
    "--method",
    "-X",
    "--input",
    "-f",
    "-F",
    "--field",
    "--raw-field",
)
_READ_FLAGS = frozenset({"--paginate", "--slurp"})


class GitHubObservationError(RuntimeError):
    """A read-only GitHub observation failed for a non-quota reason."""


class GitHubInstallationRateLimit(GitHubObservationError):
    """Every permitted delayed retry hit the shared installation quota."""


def _validate_read_arguments(arguments: Sequence[str]) -> list[str]:
    """Admit only the small REST-read grammar used by this control plane.

    ``gh api`` defaults to GET, but accepting its arbitrary option grammar
    would make that default a security property.  In particular, spellings
    such as ``--method=POST`` and ``-XPOST`` must be rejected before any
    subprocess is started.  The effect loop needs only one ``repos/...``
    endpoint plus optional pagination/slurp and a jq projection.
    """

    value = [str(argument) for argument in arguments]
    if not value:
        raise GitHubObservationError("GitHub observation omitted its API endpoint")
    if any(
        argument == option or argument.startswith(option + "=")
        or (option == "-X" and argument.startswith("-X"))
        or (option in {"-f", "-F"} and argument.startswith(option))
        for argument in value
        for option in _MUTATION_ARGUMENTS
    ):
        raise GitHubObservationError("GitHub observation wrapper forbids mutation arguments")
    endpoint: str | None = None
    index = 0
    while index < len(value):
        argument = value[index]
        if argument in _READ_FLAGS:
            index += 1
            continue
        if argument == "--jq":
            if index + 1 >= len(value) or not value[index + 1]:
                raise GitHubObservationError("GitHub observation --jq requires an expression")
            index += 2
            continue
        if argument.startswith("--jq="):
            if not argument[len("--jq=") :]:
                raise GitHubObservationError("GitHub observation --jq requires an expression")
            index += 1
            continue
        if argument.startswith("-"):
            raise GitHubObservationError(
                "GitHub observation wrapper permits only --paginate, --slurp, and --jq"
            )
        if endpoint is not None or not argument.startswith("repos/"):
            raise GitHubObservationError(
                "GitHub observation requires exactly one repository REST endpoint"
            )
        endpoint = argument
        index += 1
    if endpoint is None:
        raise GitHubObservationError("GitHub observation omitted its repository REST endpoint")
    return value


def run_gh_api_read(
    arguments: Sequence[str],
    *,
    runner: Callable[..., Any] = subprocess.run,
    sleeper: Callable[[float], None] = time.sleep,
) -> str:
    """Return one exact GET observation or raise a typed bounded failure."""

    args = _validate_read_arguments(arguments)
    last_error = ""
    for attempt, delay in enumerate(GITHUB_READ_RATE_LIMIT_BACKOFF_SECONDS):
        if delay:
            sleeper(delay)
        completed = runner(
            ["gh", "api", *args],
            text=True,
            capture_output=True,
            check=False,
        )
        stdout = str(getattr(completed, "stdout", "") or "")
        stderr = str(getattr(completed, "stderr", "") or "")
        if getattr(completed, "returncode", 1) == 0:
            return stdout
        last_error = (stderr + "\n" + stdout).strip()
        if GITHUB_INSTALLATION_RATE_LIMIT_MARKER not in last_error:
            raise GitHubObservationError(
                "GitHub read observation failed: " + (last_error or "no diagnostic")
            )
        if attempt + 1 == len(GITHUB_READ_RATE_LIMIT_BACKOFF_SECONDS):
            raise GitHubInstallationRateLimit(GITHUB_INSTALLATION_RATE_LIMIT_BLOCKER)
    raise AssertionError("bounded GitHub observation exited without a result")


def run_gh_api_read_to_file(
    arguments: Sequence[str],
    destination: pathlib.Path,
    *,
    runner: Callable[..., Any] = subprocess.run,
    sleeper: Callable[[float], None] = time.sleep,
) -> None:
    """Atomically retain one binary GET observation at ``destination``.

    Artifact archives are evidence bytes, not text.  Passing them through
    ``stdout`` would permit decoding or partial-write ambiguity, so the same
    strict GET grammar and bounded quota policy write a temporary file through
    ``gh api --output`` and atomically publish it only after an acknowledged
    observation.  The caller still cannot pass arbitrary ``gh`` flags.
    """

    args = _validate_read_arguments(arguments)
    destination = pathlib.Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=destination.name + ".",
        suffix=".tmp",
    )
    os.close(descriptor)
    # gh creates the output itself.  Do not let a pre-existing empty temporary
    # file become an accidental successful artifact.
    os.unlink(temporary_name)
    last_error = ""
    try:
        for attempt, delay in enumerate(GITHUB_READ_RATE_LIMIT_BACKOFF_SECONDS):
            if delay:
                sleeper(delay)
            completed = runner(
                ["gh", "api", "--output", temporary_name, *args],
                text=True,
                capture_output=True,
                check=False,
            )
            stdout = str(getattr(completed, "stdout", "") or "")
            stderr = str(getattr(completed, "stderr", "") or "")
            if getattr(completed, "returncode", 1) == 0:
                if not os.path.isfile(temporary_name):
                    raise GitHubObservationError(
                        "GitHub binary read acknowledged without an output file"
                    )
                with open(temporary_name, "rb") as stream:
                    os.fsync(stream.fileno())
                os.replace(temporary_name, destination)
                directory = os.open(destination.parent, os.O_RDONLY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
                return
            last_error = (stderr + "\n" + stdout).strip()
            if GITHUB_INSTALLATION_RATE_LIMIT_MARKER not in last_error:
                raise GitHubObservationError(
                    "GitHub binary read observation failed: " + (last_error or "no diagnostic")
                )
            if attempt + 1 == len(GITHUB_READ_RATE_LIMIT_BACKOFF_SECONDS):
                raise GitHubInstallationRateLimit(GITHUB_INSTALLATION_RATE_LIMIT_BLOCKER)
        raise AssertionError("bounded GitHub binary observation exited without a result")
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    destination: pathlib.Path | None = None
    if args[:1] == ["--write-bytes"]:
        if len(args) < 2 or not args[1]:
            print("--write-bytes requires a destination", file=sys.stderr)
            return 1
        destination = pathlib.Path(args[1])
        args = args[2:]
    if args[:1] == ["--"]:
        args = args[1:]
    try:
        if destination is None:
            sys.stdout.write(run_gh_api_read(args))
        else:
            run_gh_api_read_to_file(args, destination)
    except GitHubInstallationRateLimit:
        print(GITHUB_INSTALLATION_RATE_LIMIT_BLOCKER, file=sys.stderr)
        return RATE_LIMIT_EXIT_STATUS
    except GitHubObservationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
