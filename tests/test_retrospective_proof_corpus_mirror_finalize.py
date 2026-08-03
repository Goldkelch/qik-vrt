from __future__ import annotations

import copy
import contextlib
import hashlib
import inspect
import json
import os
import pathlib
import subprocess
import tempfile
import types
import unittest
from unittest import mock

from tools import qikvrt_retrospective_proof_corpus_mirror_finalize as mirror
from tools import qikvrt_retrospective_proof_corpus_zenodo_publication_controls as controls
from tools import qikvrt_retrospective_proof_corpus_zenodo_recovery as recovery
from tools import qikvrt_zenodo_publish as publish


ROOT = pathlib.Path(__file__).resolve().parents[1]
HEAD = "1" * 40
TREE = "2" * 40


def manifest_value(files: list[dict[str, object]] | None = None) -> dict[str, object]:
    if files is None:
        files = [
            {
                "path": f"release/file-{index}.bin",
                "name": f"file-{index}.bin",
                "size": 1,
                "md5": hashlib.md5(bytes([index])).hexdigest(),  # noqa: S324
                "sha256": hashlib.sha256(bytes([index])).hexdigest(),
                "git_blob_sha": "3" * 40,
            }
            for index in range(65)
        ]
    return {
        "schema": publish.SCHEMA_V2,
        "repository": mirror.AUTHORITY,
        "source_head": controls.SOURCE_HEAD,
        "manifest_sha256": "4" * 64,
        "metadata": {
            "title": (
                "QIK-VRT Retrospective Proof Corpus: 19 subjects and 70,439 "
                "machine-readable claim dispositions"
            ),
            "version": "2026-07-28-v3",
        },
        "files": files,
        "machine_proof": {"sha256": controls.MACHINE_PROOF_SHA256},
        "owner_authorization": {"authorization_id": controls.AUTHORIZATION_ID},
    }


def evidence_value(manifest: dict[str, object] | None = None) -> dict[str, object]:
    manifest = manifest or manifest_value()
    return {
        "schema": publish.EVIDENCE_SCHEMA_V2,
        "state": "published",
        "phase": "public_verified",
        "manifest_path": mirror.MANIFEST_REL,
        "manifest_sha256": manifest["manifest_sha256"],
        "machine_proof": manifest["machine_proof"],
        "owner_authorization": manifest["owner_authorization"],
        "remote_consumption": {},
        "repository": mirror.AUTHORITY,
        "repository_commit": "5" * 40,
        "source_head": controls.SOURCE_HEAD,
        "binding": {},
        "governance_boundaries": list(publish.GOVERNANCE_BOUNDARIES),
        "recovery": publish._recovery_flags("public_verified"),
        "record_id": 12345678,
        "doi": "10.5281/zenodo.12345678",
        "title": manifest["metadata"]["title"],  # type: ignore[index]
        "version": manifest["metadata"]["version"],  # type: ignore[index]
        "files": manifest["files"],
        "conceptdoi": "10.5281/zenodo.12345677",
        "record_url": "https://zenodo.org/records/12345678",
    }


@contextlib.contextmanager
def publication_binding_fixture(
    *,
    recovery_subject: str = recovery.RECOVERY_COMMIT_SUBJECT,
    checkpoint_count: int = 1,
):
    key = "c" * 64
    tag = "d" * 40
    recovery_ref = recovery.RECOVERY_REF_PREFIX + key
    consumption_ref = publish._remote_consumption_ref(key)
    manifest = manifest_value()
    manifest["owner_authorization"] = {
        "authorization_id": controls.AUTHORIZATION_ID,
        "consumption_key": {"value": key},
        "remote_consumption_ref": consumption_ref,
    }
    manifest_raw = mirror.json_bytes(manifest)
    with tempfile.TemporaryDirectory(
        prefix="mirror-publication-binding-", dir="/tmp"
    ) as temporary:
        repository = pathlib.Path(temporary) / "repository"
        repository.mkdir()
        subprocess.run(
            ["git", "init", "--quiet", "--initial-branch=publication"],
            cwd=repository,
            check=True,
        )
        commit_environment = {
            **os.environ,
            "GIT_AUTHOR_NAME": "test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
            "GIT_AUTHOR_DATE": "2026-08-03T10:00:00+00:00",
            "GIT_COMMITTER_DATE": "2026-08-03T10:00:00+00:00",
        }

        def write(relative: str, raw: bytes) -> None:
            path = repository.joinpath(*pathlib.PurePosixPath(relative).parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)

        def commit(subject: str) -> str:
            subprocess.run(["git", "add", "-A"], cwd=repository, check=True)
            subprocess.run(
                ["git", "commit", "--quiet", "-m", subject],
                cwd=repository,
                env=commit_environment,
                check=True,
            )
            return subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repository, text=True
            ).strip()

        write("base.txt", b"base\n")
        for path, status in mirror.EXECUTION_DELTA_STATUSES.items():
            if status == "M":
                write(path, b"base-integrity\n")
        base = commit("control base")
        for path in mirror.EXECUTION_DELTA_STATUSES:
            write(path, manifest_raw if path == mirror.MANIFEST_REL else b"execution\n")
        execution = commit("materialize exact publication execution")
        evidence = evidence_value(manifest)
        evidence["repository_commit"] = execution
        evidence["remote_consumption"] = {
            "remote": "github_git_data_api",
            "api_origin": "https://api.github.com",
            "repository": mirror.AUTHORITY,
            "ref": consumption_ref,
            "tag_object": tag,
            "object_type": "tag",
            "execution_head": execution,
            "acquisition": "GITHUB_GIT_DATA_REST_CREATE_ONLY",
            "recovery_mode": "NEWLY_CREATED_REF",
        }
        evidence_raw = mirror.json_bytes(evidence)
        recovery_head = execution
        for index in range(checkpoint_count):
            journal_raw = (
                '{"phase":"publish_requested","test_sequence":'
                + str(index)
                + "}\n"
            ).encode("ascii")
            write(recovery.RECOVERY_RELATIVE, journal_raw)
            recovery_head = commit(recovery_subject)
        for path in mirror.INTEGRITY_PATHS:
            write(path, b"final-integrity\n")
        write(mirror.EVIDENCE_REL, evidence_raw)
        final = commit(recovery.PUBLICATION_COMMIT_SUBJECT)
        context = types.SimpleNamespace(
            publication_ref=mirror.PUBLICATION_REF,
            recovery_ref=recovery_ref,
            consumption=types.SimpleNamespace(
                ref=consumption_ref,
                tag_object=tag,
            ),
        )
        yield {
            "repository": repository,
            "base": base,
            "execution": execution,
            "recovery_head": recovery_head,
            "final": final,
            "manifest": manifest,
            "manifest_raw": manifest_raw,
            "evidence": evidence,
            "evidence_raw": evidence_raw,
            "context": context,
            "recovery_ref": recovery_ref,
            "consumption_ref": consumption_ref,
            "tag": tag,
        }


def validate_binding_fixture(
    fixture: dict[str, object],
    *,
    ref_overrides: dict[str, str | None] | None = None,
    require_public_ref: bool = True,
    chain_values: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    refs: dict[str, str | None] = {
        mirror.PUBLICATION_REF: str(fixture["final"]),
        str(fixture["recovery_ref"]): str(fixture["recovery_head"]),
        str(fixture["consumption_ref"]): str(fixture["tag"]),
    }
    if require_public_ref:
        refs[mirror.PUBLIC_REF] = str(fixture["final"])
    refs.update(ref_overrides or {})

    def read_ref(
        repository: str,
        ref: str,
        *,
        missing_ok: bool = False,
        additional_refs=(),
    ) -> str | None:
        del additional_refs
        if repository != mirror.AUTHORITY:
            raise AssertionError("unexpected repository")
        if ref not in refs:
            if missing_ok:
                return None
            raise AssertionError("unexpected ref read: " + ref)
        value = refs[ref]
        if value is None and not missing_ok:
            raise mirror.MirrorFinalizeError("test ref is absent")
        return value

    values = (
        [{"phase": "publish_requested"}]
        if chain_values is None
        else chain_values
    )
    with (
        mock.patch.object(mirror, "ROOT", fixture["repository"]),
        mock.patch.object(recovery, "CONTROL_BASE_HEAD", fixture["base"]),
        mock.patch.object(recovery, "load_frozen_contract", return_value=object()),
        mock.patch.object(recovery, "make_context", return_value=fixture["context"]),
        mock.patch.object(recovery, "validate_recovery_chain", return_value=values),
        mock.patch.object(recovery, "validate_ref_state") as validate_refs,
        mock.patch.object(mirror, "anonymous_git_ref", side_effect=read_ref),
    ):
        result = mirror.validate_publication_binding_anonymous(
            manifest_raw=fixture["manifest_raw"],
            evidence_raw=fixture["evidence_raw"],
            manifest=fixture["manifest"],
            evidence=fixture["evidence"],
            head=str(fixture["final"]),
            require_public_ref=require_public_ref,
        )
    validate_refs.assert_called_once()
    return result


class FakeTransport:
    pass


class RetrospectiveProofCorpusMirrorFinalizeTests(unittest.TestCase):
    def test_workflow_is_narrow_create_event_and_has_no_zenodo_credential(self) -> None:
        workflow = (
            ROOT
            / ".github/workflows/qikvrt_retrospective_proof_corpus_mirror_finalize.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("evidence/retrospective-proof-corpus-public-verified-v3", workflow)
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertIn("QIKVRT_MESH_TOKEN: ${{ secrets.QIKVRT_MESH_TOKEN }}", workflow)
        self.assertNotIn("ZENODO_TOKEN", workflow)
        self.assertNotIn("secrets.ZENODO", workflow)
        self.assertNotIn("--force", workflow)
        self.assertNotIn("refs/heads/main", workflow)
        self.assertNotIn("    paths:", workflow)
        self.assertIn("tests.test_retrospective_proof_corpus_mirror_finalize", workflow)

    def test_anonymous_transport_source_disables_proxy_redirect_and_auth(self) -> None:
        source = (
            ROOT / "tools/qikvrt_retrospective_proof_corpus_mirror_finalize.py"
        ).read_text(encoding="utf-8")
        self.assertIn("urllib.request.ProxyHandler({})", source)
        self.assertIn("ssl.create_default_context()", source)
        self.assertIn("NoRedirect()", source)
        self.assertIn('key.casefold() == "authorization"', source)
        self.assertNotIn('headers={"Authorization"', source)

    def test_json_parser_rejects_duplicates_nonfinite_and_surrogates(self) -> None:
        self.assertEqual(mirror.parse_json(b'{"value":1}', "test"), {"value": 1})
        for raw in (
            b'{"value":1,"value":2}',
            b'{"outer":{"value":1,"value":2}}',
            b'{"value":NaN}',
            b'{"value":Infinity}',
            b'{"value":1e9999}',
            b'{"value":-1e9999}',
            b'{"value":"\\ud800"}',
        ):
            with self.subTest(raw=raw), self.assertRaises(mirror.MirrorFinalizeError):
                mirror.parse_json(raw, "test")

    def test_anonymous_url_queries_are_exactly_bounded(self) -> None:
        commit = "1" * 40
        self.assertEqual(
            mirror.AnonymousHTTPS._validate_url(
                "https://api.github.com/repos/Goldkelch/qik-vrt/contents/a?ref="
                + commit
            ),
            "https://api.github.com/repos/Goldkelch/qik-vrt/contents/a?ref="
            + commit,
        )
        self.assertEqual(
            mirror.AnonymousHTTPS._validate_url(
                "https://zenodo.org/api/records/123"
            ),
            "https://zenodo.org/api/records/123",
        )
        for url in (
            "https://zenodo.org/api/records/123?token=secret",
            "https://api.github.com/repos/Goldkelch/qik-vrt/git/ref/x?token=secret",
            "https://api.github.com/repos/Goldkelch/qik-vrt/contents/a?ref=bad",
            "https://api.github.com/repos/Goldkelch/qik-vrt/contents/a?ref="
            + commit
            + "&ref="
            + commit,
            "https://api.github.com/repos/Goldkelch/qik-vrt/contents/a?token=x",
        ):
            with self.subTest(url=url), self.assertRaises(mirror.MirrorFinalizeError):
                mirror.AnonymousHTTPS._validate_url(url)

    def test_source_contract_is_non_effectful_and_scope_fixed(self) -> None:
        report = mirror.source_check()
        self.assertEqual(report["state"], "SOURCE_CONTRACT_PASS")
        self.assertEqual(report["effect_state"], "EFFECT_ACK_CONTINUE")
        self.assertFalse(report["ordinary_release"])
        self.assertFalse(report["network_effect"])
        self.assertFalse(report["git_effect"])
        self.assertEqual(mirror.PUBLIC_REF.count("main"), 0)
        self.assertEqual(mirror.OVERVIEW_REF.count("main"), 0)
        self.assertEqual(mirror.EQUALITY_REF.count("main"), 0)
        self.assertEqual(len({mirror.PUBLIC_REF, mirror.OVERVIEW_REF, mirror.EQUALITY_REF}), 3)

    def test_only_mesh_token_is_accepted(self) -> None:
        token = "mesh-token-value-1234567890"
        self.assertEqual(
            mirror.require_mesh_token({mirror.MESH_TOKEN_ENV: token}), token
        )
        for forbidden in ("ZENODO_TOKEN", "QIKVRT_ZENODO_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
            with self.subTest(forbidden=forbidden):
                with self.assertRaisesRegex(mirror.MirrorFinalizeError, "only QIKVRT_MESH_TOKEN"):
                    mirror.require_mesh_token(
                        {mirror.MESH_TOKEN_ENV: token, forbidden: "secret-secret-secret-secret"}
                    )
        for bad in (None, "short", "contains whitespace 123456789"):
            environment = {} if bad is None else {mirror.MESH_TOKEN_ENV: bad}
            with self.assertRaisesRegex(mirror.MirrorFinalizeError, "missing or structurally invalid"):
                mirror.require_mesh_token(environment)

    def test_event_must_be_create_only_non_force(self) -> None:
        event = {
            "GITHUB_REPOSITORY": mirror.AUTHORITY,
            "GITHUB_REF": mirror.PUBLIC_REF,
            "GITHUB_SHA": HEAD,
            "QIKVRT_EVENT_CREATED": "true",
            "QIKVRT_EVENT_DELETED": "false",
            "QIKVRT_EVENT_FORCED": "false",
            "QIKVRT_EVENT_BEFORE": mirror.ZERO40,
            "QIKVRT_EVENT_AFTER": HEAD,
        }
        mirror.verify_event(event, HEAD)
        for key, bad in (
            ("QIKVRT_EVENT_CREATED", "false"),
            ("QIKVRT_EVENT_FORCED", "true"),
            ("QIKVRT_EVENT_BEFORE", "9" * 40),
            ("GITHUB_REF", "refs/heads/main"),
        ):
            changed = {**event, key: bad}
            with self.assertRaisesRegex(mirror.MirrorFinalizeError, "create-only/non-force"):
                mirror.verify_event(changed, HEAD)

    def test_git_push_uses_only_exact_empty_old_cas_and_rejects_race(self) -> None:
        token = "mesh-token-value-1234567890"
        with mock.patch.object(
            mirror,
            "git_output",
            return_value=(
                b"*\t1111111111111111111111111111111111111111:"
                b"refs/heads/evidence/retrospective-proof-corpus-overview-v3\t"
                b"[new branch]\n"
            ),
        ) as git:
            mirror.push_create_only(
                mirror.AUTHORITY, HEAD, mirror.OVERVIEW_REF, token
            )
        arguments = git.call_args.args[0]
        self.assertIn(
            "--force-with-lease=" + mirror.OVERVIEW_REF + ":", arguments
        )
        self.assertNotIn("--force", arguments)
        self.assertNotIn(token, " ".join(arguments))
        self.assertEqual(git.call_count, 1)

        with mock.patch.object(
            mirror,
            "git_output",
            return_value=b"=\tref:ref\t[up to date]\n",
        ) as raced:
            with self.assertRaisesRegex(
                mirror.MirrorFinalizeError, "did not create a new non-force ref"
            ):
                mirror.push_create_only(
                    mirror.AUTHORITY, HEAD, mirror.OVERVIEW_REF, token
                )
        self.assertEqual(raced.call_count, 1)

    def test_create_only_ref_resumes_exact_and_reconciles_ambiguity(self) -> None:
        token = "mesh-token-value-1234567890"
        with (
            mock.patch.object(mirror, "anonymous_git_ref", return_value=HEAD),
            mock.patch.object(mirror, "push_create_only") as push,
        ):
            self.assertFalse(
                mirror.ensure_create_only_ref(
                    mirror.MIRROR, mirror.PUBLIC_REF, HEAD, token
                )
            )
        push.assert_not_called()

        with (
            mock.patch.object(mirror, "anonymous_git_ref", return_value="9" * 40),
            mock.patch.object(mirror, "push_create_only") as divergent_push,
        ):
            with self.assertRaisesRegex(
                mirror.MirrorFinalizeError, "existing finalization ref is divergent"
            ):
                mirror.ensure_create_only_ref(
                    mirror.MIRROR, mirror.PUBLIC_REF, HEAD, token
                )
        divergent_push.assert_not_called()

        for mutation_error in (None, mirror.MirrorFinalizeError("ambiguous")):
            with self.subTest(mutation_error=mutation_error):
                push_effect = (
                    mock.Mock(side_effect=mutation_error)
                    if mutation_error is not None
                    else mock.Mock()
                )
                with (
                    mock.patch.object(
                        mirror, "anonymous_git_ref", side_effect=[None, HEAD]
                    ),
                    mock.patch.object(mirror, "push_create_only", push_effect),
                ):
                    self.assertTrue(
                        mirror.ensure_create_only_ref(
                            mirror.MIRROR, mirror.PUBLIC_REF, HEAD, token
                        )
                    )
                self.assertEqual(push_effect.call_count, 1)

        with (
            mock.patch.object(mirror, "anonymous_git_ref", side_effect=[None, None]),
            mock.patch.object(
                mirror,
                "push_create_only",
                side_effect=mirror.MirrorFinalizeError("ambiguous"),
            ) as absent_push,
        ):
            with self.assertRaisesRegex(
                mirror.MirrorFinalizeError, "remained absent after one mutation"
            ):
                mirror.ensure_create_only_ref(
                    mirror.MIRROR, mirror.PUBLIC_REF, HEAD, token
                )
        self.assertEqual(absent_push.call_count, 1)

    def test_anonymous_git_ref_clears_credentials_and_proxies(self) -> None:
        with mock.patch.object(
            mirror,
            "git_output",
            return_value=(HEAD + "\t" + mirror.PUBLIC_REF + "\n").encode("ascii"),
        ) as git:
            self.assertEqual(
                mirror.anonymous_git_ref(mirror.AUTHORITY, mirror.PUBLIC_REF), HEAD
            )
        arguments = git.call_args.args[0]
        joined = " ".join(arguments)
        self.assertIn("credential.helper=", arguments)
        self.assertIn("http.extraHeader=", arguments)
        self.assertIn("http.proxy=", arguments)
        self.assertIn("https.proxy=", arguments)
        self.assertIn("ls-remote --refs", joined)
        self.assertNotIn("token", joined.casefold())

    def test_raw_commit_parent_survives_depth_one_fetch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mirror-shallow-test-", dir="/tmp") as temporary:
            base = pathlib.Path(temporary)
            source = base / "source"
            remote = base / "remote.git"
            checkout = base / "checkout"
            source.mkdir()
            subprocess.run(
                ["git", "init", "--quiet", "--initial-branch=main"],
                cwd=source,
                check=True,
            )
            commit_environment = {
                **os.environ,
                "GIT_AUTHOR_NAME": "test",
                "GIT_AUTHOR_EMAIL": "test@example.invalid",
                "GIT_COMMITTER_NAME": "test",
                "GIT_COMMITTER_EMAIL": "test@example.invalid",
            }
            (source / "value").write_text("one\n", encoding="utf-8")
            subprocess.run(["git", "add", "value"], cwd=source, check=True)
            subprocess.run(
                ["git", "commit", "--quiet", "-m", "parent"],
                cwd=source,
                env=commit_environment,
                check=True,
            )
            parent = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=source, text=True
            ).strip()
            (source / "value").write_text("two\n", encoding="utf-8")
            subprocess.run(["git", "add", "value"], cwd=source, check=True)
            subprocess.run(
                ["git", "commit", "--quiet", "-m", "child"],
                cwd=source,
                env=commit_environment,
                check=True,
            )
            subprocess.run(
                ["git", "clone", "--quiet", "--bare", str(source), str(remote)],
                check=True,
            )
            checkout.mkdir()
            subprocess.run(["git", "init", "--quiet"], cwd=checkout, check=True)
            subprocess.run(
                [
                    "git",
                    "fetch",
                    "--quiet",
                    "--depth=1",
                    "file://" + str(remote),
                    "refs/heads/main",
                ],
                cwd=checkout,
                check=True,
            )
            self.assertEqual(
                subprocess.check_output(
                    ["git", "show", "-s", "--format=%P", "FETCH_HEAD"],
                    cwd=checkout,
                    text=True,
                ).strip(),
                "",
            )
            envelope = mirror.raw_commit_envelope(checkout, "FETCH_HEAD")
            self.assertEqual(envelope["parents"], [parent])
            self.assertRegex(envelope["tree"], r"^[0-9a-f]{40}$")

    def test_publication_binding_accepts_only_the_exact_public_event_head(self) -> None:
        with publication_binding_fixture() as fixture:
            result = validate_binding_fixture(fixture)
            self.assertEqual(result["execution_head"], fixture["execution"])
            self.assertEqual(result["publication_head"], fixture["final"])
            self.assertEqual(result["recovery_head"], fixture["recovery_head"])
            self.assertEqual(result["consumption_tag_object"], fixture["tag"])
            self.assertEqual(result["terminal_recovery_phase"], "publish_requested")
            with self.assertRaisesRegex(
                mirror.MirrorFinalizeError, "public_verified ref differs"
            ):
                validate_binding_fixture(
                    fixture,
                    ref_overrides={mirror.PUBLIC_REF: "f" * 40},
                )

    def test_publication_binding_allows_absent_public_ref_only_before_bootstrap(self) -> None:
        with publication_binding_fixture() as fixture:
            result = validate_binding_fixture(
                fixture,
                require_public_ref=False,
            )
            self.assertIsNone(result["public_ref_head"])
            with self.assertRaises(mirror.MirrorFinalizeError):
                validate_binding_fixture(
                    fixture,
                    ref_overrides={mirror.PUBLIC_REF: None},
                    require_public_ref=True,
                )

    def test_publication_binding_rejects_chain_subject_and_live_ref_tampering(self) -> None:
        with publication_binding_fixture(recovery_subject="wrong subject") as fixture:
            with self.assertRaisesRegex(
                mirror.MirrorFinalizeError, "recovery commit subject"
            ):
                validate_binding_fixture(fixture)
        with publication_binding_fixture() as fixture:
            for ref, message in (
                (mirror.PUBLICATION_REF, "publication ref differs"),
                (str(fixture["recovery_ref"]), "recovery ref differs"),
                (str(fixture["consumption_ref"]), "consumption ref differs"),
            ):
                with self.subTest(ref=ref), self.assertRaisesRegex(
                    mirror.MirrorFinalizeError, message
                ):
                    validate_binding_fixture(
                        fixture,
                        ref_overrides={ref: "e" * 40},
                    )

    def test_publication_binding_rejects_empty_and_over_135_checkpoint_chains(self) -> None:
        with publication_binding_fixture(checkpoint_count=0) as fixture:
            with self.assertRaisesRegex(
                mirror.MirrorFinalizeError, "cumulative 5-path"
            ):
                validate_binding_fixture(fixture)
        with publication_binding_fixture(checkpoint_count=136) as fixture:
            with self.assertRaisesRegex(
                mirror.MirrorFinalizeError, "exceeds 135 checkpoints"
            ):
                validate_binding_fixture(fixture)

    def test_public_verified_evidence_is_strict_and_65_file_bound(self) -> None:
        manifest = manifest_value()
        evidence = evidence_value(manifest)
        observed = mirror.validate_public_evidence(evidence, manifest)
        self.assertEqual(len(observed["files"]), 65)
        for key, bad in (
            ("phase", "publish_requested"),
            ("state", "EFFECT_RELEASED/AWAITING_REMOTE_RECONCILIATION"),
            ("repository", mirror.MIRROR),
            ("source_head", "0" * 40),
        ):
            changed = {**evidence, key: bad}
            with self.assertRaisesRegex(mirror.MirrorFinalizeError, "public_verified"):
                mirror.validate_public_evidence(changed, manifest)
        inflated = {**evidence, "effect_ack_done": True}
        with self.assertRaisesRegex(mirror.MirrorFinalizeError, "keys differ"):
            mirror.validate_public_evidence(inflated, manifest)

    def test_overview_projection_covers_all_three_files_and_stays_fail_closed(self) -> None:
        manifest = manifest_value()
        evidence = evidence_value(manifest)
        outputs = mirror.build_overview_files(manifest, evidence)
        self.assertEqual(
            set(outputs),
            {
                "docs/publications/index.html",
                "docs/publications/index.json",
                ".well-known/qik-vrt-self-disclosure.json",
            },
        )
        overview = json.loads(outputs["docs/publications/index.json"])
        indexed = [
            entry for entry in overview["zenodo_records"]
            if entry["id"] == controls.PUBLICATION_ID
        ]
        self.assertEqual(len(indexed), 1)
        self.assertEqual(indexed[0]["receipt_path"], mirror.EVIDENCE_REL)
        self.assertEqual(indexed[0]["file_count"], 65)
        html = outputs["docs/publications/index.html"].decode("utf-8")
        self.assertIn(evidence["doi"], html)
        disclosure = json.loads(outputs[".well-known/qik-vrt-self-disclosure.json"])
        binding = disclosure["bindings"]["retrospective_proof_corpus_publication"]
        self.assertTrue(binding["scope_bound_only"])
        self.assertFalse(binding["repository_wide_equality_claimed"])
        self.assertEqual(
            disclosure["completion_claims"],
            {"pass": False, "final_pass": False, "effect_ack_done": False},
        )

    def test_reciprocal_receipt_does_not_preclaim_done(self) -> None:
        manifest = manifest_value()
        evidence = evidence_value(manifest)
        overview = mirror.build_overview_files(manifest, evidence)
        gate = {
            "authority_head": HEAD,
            "authority_tree": TREE,
            "record_id": evidence["record_id"],
            "doi": evidence["doi"],
            "conceptdoi": evidence["conceptdoi"],
            "manifest_sha256": evidence["manifest_sha256"],
            "evidence_sha256": "6" * 64,
            "file_count": 65,
            "total_bytes": mirror.EXPECTED_TOTAL_BYTES,
        }
        receipt = json.loads(mirror.build_receipt(gate, overview))
        self.assertEqual(receipt["effect_boundary"]["embedded_state"], "EFFECT_ACK_CONTINUE")
        self.assertFalse(receipt["effect_boundary"]["effect_ack_done"])
        self.assertFalse(receipt["effect_boundary"]["ordinary_release"])
        self.assertFalse(receipt["scope"]["main_equality_claimed"])
        self.assertFalse(receipt["scope"]["repository_wide_equality_claimed"])
        self.assertEqual(
            receipt["git_ref_acquisition"]["mode"], "GIT_CAS_CREATE_ONLY"
        )
        self.assertEqual(
            receipt["git_ref_acquisition"]["lease_contract"],
            "EXPECTED_OLD_ABSENT",
        )
        self.assertFalse(receipt["git_ref_acquisition"]["force_update_allowed"])
        self.assertEqual(len(receipt["publication_overview"]["files"]), 3)

    def test_stage_commit_updates_only_output_and_integrity_trio_in_temp_repo(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mirror-stage-test-", dir="/tmp") as temporary:
            repository = pathlib.Path(temporary) / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "--quiet"], cwd=repository, check=True)
            (repository / "docs/publications").mkdir(parents=True)
            (repository / "docs/publications/index.json").write_text("old\n", encoding="utf-8")
            for path in mirror.INTEGRITY_PATHS:
                (repository / path).write_text("old\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "."], cwd=repository, check=True
            )
            commit_environment = {
                **os.environ,
                "GIT_AUTHOR_NAME": "test",
                "GIT_AUTHOR_EMAIL": "test@example.invalid",
                "GIT_COMMITTER_NAME": "test",
                "GIT_COMMITTER_EMAIL": "test@example.invalid",
                "GIT_AUTHOR_DATE": "2026-08-03T10:00:00+00:00",
                "GIT_COMMITTER_DATE": "2026-08-03T10:00:00+00:00",
            }
            subprocess.run(
                ["git", "commit", "--quiet", "-m", "base"],
                cwd=repository, env=commit_environment, check=True,
            )
            parent = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repository, text=True
            ).strip()

            def fake_integrity(stage: pathlib.Path, action: str) -> None:
                if action == "generate":
                    for index, path in enumerate(mirror.INTEGRITY_PATHS):
                        (stage / path).write_text(f"generated-{index}\n", encoding="utf-8")
                else:
                    for index, path in enumerate(mirror.INTEGRITY_PATHS):
                        self.assertEqual(
                            (stage / path).read_text(encoding="utf-8"),
                            f"generated-{index}\n",
                        )

            with (
                mock.patch.object(mirror, "ROOT", repository),
                mock.patch.object(mirror, "_run_integrity", side_effect=fake_integrity),
                mock.patch.object(mirror, "_run_stage_overview_tests"),
                mock.patch.dict(os.environ, {"RUNNER_TEMP": temporary}, clear=False),
            ):
                commit, tree = mirror.create_verified_stage_commit(
                    parent,
                    {"docs/publications/index.json": b"new\n"},
                    b"stage\n",
                )
            self.assertRegex(commit, r"^[0-9a-f]{40}$")
            self.assertRegex(tree, r"^[0-9a-f]{40}$")
            self.assertEqual(
                subprocess.check_output(
                    ["git", "show", f"{commit}:docs/publications/index.json"],
                    cwd=repository,
                ),
                b"new\n",
            )
            self.assertEqual(
                subprocess.check_output(
                    ["git", "show", "-s", "--format=%P", commit],
                    cwd=repository, text=True,
                ).strip(),
                parent,
            )
            changed = subprocess.check_output(
                ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit],
                cwd=repository, text=True,
            ).splitlines()
            self.assertEqual(
                sorted(changed),
                sorted(["docs/publications/index.json", *mirror.INTEGRITY_PATHS]),
            )
            self.assertEqual(
                subprocess.check_output(
                    ["git", "status", "--porcelain"], cwd=repository, text=True
                ),
                "",
            )

    def test_finalize_orders_two_public_gates_and_guards_every_ref_ensure(self) -> None:
        manifest = manifest_value()
        evidence = evidence_value(manifest)
        environment = {
            mirror.MESH_TOKEN_ENV: "mesh-token-value-1234567890",
            "GITHUB_REPOSITORY": mirror.AUTHORITY,
            "GITHUB_REF": mirror.PUBLIC_REF,
            "GITHUB_SHA": HEAD,
            "QIKVRT_EVENT_CREATED": "true",
            "QIKVRT_EVENT_DELETED": "false",
            "QIKVRT_EVENT_FORCED": "false",
            "QIKVRT_EVENT_BEFORE": mirror.ZERO40,
            "QIKVRT_EVENT_AFTER": HEAD,
        }
        gate = {
            "authority_head": HEAD,
            "authority_tree": TREE,
            "record_id": evidence["record_id"],
            "doi": evidence["doi"],
            "conceptdoi": evidence["conceptdoi"],
            "manifest_sha256": evidence["manifest_sha256"],
            "evidence_sha256": "7" * 64,
            "file_count": 65,
            "total_bytes": mirror.EXPECTED_TOTAL_BYTES,
        }
        equality_commit = "8" * 40
        equality_tree = "9" * 40
        overview_commit = "a" * 40
        overview_tree = "b" * 40
        def fake_read_ref(_transport, repository, ref, missing_ok=False):
            if missing_ok:
                return None
            if ref == mirror.EQUALITY_REF:
                return equality_commit
            if ref == mirror.OVERVIEW_REF:
                return overview_commit
            return HEAD

        with (
            mock.patch.object(mirror, "verify_authority_gate", side_effect=[gate, copy.deepcopy(gate)]) as public_gate,
            mock.patch.object(mirror, "verify_guard_unchanged") as guard,
            mock.patch.object(mirror, "verify_pair", return_value={"commit": HEAD, "tree": TREE, "parents": []}) as pair,
            mock.patch.object(mirror, "ensure_create_only_ref", return_value=True) as ensure,
            mock.patch.object(mirror, "build_overview_files", return_value={"docs/publications/index.html": b"html", "docs/publications/index.json": b"{}\n", ".well-known/qik-vrt-self-disclosure.json": b"{}\n"}),
            mock.patch.object(mirror, "create_verified_stage_commit", side_effect=[(overview_commit, overview_tree), (equality_commit, equality_tree)]),
            mock.patch.object(mirror, "verify_remote_integrity_anonymous") as public_integrity,
            mock.patch.object(mirror, "verify_pair_integrity_anonymous") as pair_integrity,
            mock.patch.object(mirror, "emit_frame"),
        ):
            report = mirror.finalize(
                transport=FakeTransport(), environment=environment,
                manifest_raw=b"manifest", evidence_raw=b"evidence",
                manifest=manifest, evidence=evidence, head=HEAD,
            )
        self.assertEqual(public_gate.call_count, 2)
        self.assertEqual(guard.call_count, 5)
        self.assertEqual(ensure.call_count, 5)
        self.assertEqual(pair.call_count, 10)
        self.assertEqual(
            [call.args[1] for call in pair.call_args_list[-3:]],
            [mirror.PUBLIC_REF, mirror.OVERVIEW_REF, mirror.EQUALITY_REF],
        )
        self.assertEqual(public_integrity.call_count, 1)
        self.assertEqual(pair_integrity.call_count, 2)
        self.assertEqual(report["effect_state"], "EFFECT_ACK_DONE")
        self.assertTrue(report["effect_scope_bound"])
        self.assertFalse(report["scope"]["main_equality_claimed"])
        self.assertFalse(report["scope"]["repository_wide_equality_claimed"])

    def test_mutation_guard_rebinds_all_four_live_authority_refs(self) -> None:
        recovery_ref = recovery.RECOVERY_REF_PREFIX + "c" * 64
        consumption_ref = publish._remote_consumption_ref("c" * 64)
        gate = {
            "authority_head": HEAD,
            "authority_tree": TREE,
            "publication_head": "3" * 40,
            "recovery_ref": recovery_ref,
            "recovery_head": "4" * 40,
            "consumption_ref": consumption_ref,
            "consumption_tag_object": "5" * 40,
        }
        expected = {
            mirror.PUBLIC_REF: HEAD,
            mirror.PUBLICATION_REF: gate["publication_head"],
            recovery_ref: gate["recovery_head"],
            consumption_ref: gate["consumption_tag_object"],
        }

        def run(overrides: dict[str, str] | None = None) -> None:
            observed = {**expected, **(overrides or {})}
            with (
                mock.patch.object(
                    mirror,
                    "anonymous_git_ref",
                    side_effect=lambda _repository, ref, **_kwargs: observed[ref],
                ),
                mock.patch.object(
                    mirror,
                    "local_commit",
                    return_value={"tree": TREE, "parents": []},
                ),
                mock.patch.object(
                    mirror,
                    "local_content",
                    side_effect=lambda _head, path: (
                        b"manifest" if path == mirror.MANIFEST_REL else b"evidence"
                    ),
                ),
            ):
                mirror.verify_guard_unchanged(
                    FakeTransport(), gate, b"manifest", b"evidence"
                )

        run()
        for ref, message in (
            (mirror.PUBLIC_REF, "public_verified ref moved"),
            (mirror.PUBLICATION_REF, "publication ref moved"),
            (recovery_ref, "recovery ref moved"),
            (consumption_ref, "consumption ref moved"),
        ):
            with self.subTest(ref=ref), self.assertRaisesRegex(
                mirror.MirrorFinalizeError, message
            ):
                run({ref: "f" * 40})

    def test_authority_public_ref_bootstrap_fresh_and_exact_existing_are_continue(self) -> None:
        stable = {
            "execution_head": "2" * 40,
            "publication_head": HEAD,
            "recovery_ref": recovery.RECOVERY_REF_PREFIX + "c" * 64,
            "recovery_head": "3" * 40,
            "consumption_ref": publish._remote_consumption_ref("c" * 64),
            "consumption_tag_object": "4" * 40,
            "recovery_checkpoint_count": 72,
            "terminal_recovery_phase": "publish_requested",
        }
        before = {**stable, "public_ref_head": None}
        after = {**stable, "public_ref_head": HEAD}
        environment = {mirror.MESH_TOKEN_ENV: "mesh-token-value-1234567890"}
        for created in (True, False):
            with self.subTest(created=created):
                with (
                    mock.patch.object(
                        mirror,
                        "validate_publication_binding_anonymous",
                        side_effect=[before, after],
                    ) as binding,
                    mock.patch.object(
                        mirror, "ensure_create_only_ref", return_value=created
                    ) as ensure,
                ):
                    report = mirror.bootstrap_authority_public_ref(
                        environment=environment,
                        manifest_raw=b"manifest",
                        evidence_raw=b"evidence",
                        manifest={},
                        evidence={},
                        head=HEAD,
                    )
            self.assertEqual(binding.call_count, 2)
            self.assertFalse(binding.call_args_list[0].kwargs["require_public_ref"])
            self.assertTrue(binding.call_args_list[1].kwargs["require_public_ref"])
            ensure.assert_called_once_with(
                mirror.AUTHORITY,
                mirror.PUBLIC_REF,
                HEAD,
                environment[mirror.MESH_TOKEN_ENV],
            )
            self.assertEqual(report["effect_state"], "EFFECT_ACK_CONTINUE")
            self.assertFalse(report["ordinary_release"])
            self.assertEqual(report["created"], created)
            self.assertEqual(report["exact_existing_resume"], not created)
            self.assertNotIn("EFFECT_ACK_" + "DONE", json.dumps(report))

    def test_authority_public_ref_bootstrap_divergent_existing_blocks(self) -> None:
        before = {
            "execution_head": "2" * 40,
            "publication_head": HEAD,
            "recovery_ref": recovery.RECOVERY_REF_PREFIX + "c" * 64,
            "recovery_head": "3" * 40,
            "consumption_ref": publish._remote_consumption_ref("c" * 64),
            "consumption_tag_object": "4" * 40,
            "public_ref_head": None,
            "recovery_checkpoint_count": 72,
            "terminal_recovery_phase": "publish_requested",
        }
        with (
            mock.patch.object(
                mirror,
                "validate_publication_binding_anonymous",
                return_value=before,
            ) as binding,
            mock.patch.object(
                mirror,
                "ensure_create_only_ref",
                side_effect=mirror.MirrorFinalizeError(
                    "existing finalization ref is divergent"
                ),
            ),
        ):
            with self.assertRaisesRegex(
                mirror.MirrorFinalizeError, "existing finalization ref is divergent"
            ):
                mirror.bootstrap_authority_public_ref(
                    environment={
                        mirror.MESH_TOKEN_ENV: "mesh-token-value-1234567890"
                    },
                    manifest_raw=b"manifest",
                    evidence_raw=b"evidence",
                    manifest={},
                    evidence={},
                    head=HEAD,
                )
        self.assertEqual(binding.call_count, 1)
        self.assertFalse(binding.call_args.kwargs["require_public_ref"])

    def test_final_public_gate_drift_blocks_done(self) -> None:
        manifest = manifest_value()
        evidence = evidence_value(manifest)
        first = {
            "authority_head": HEAD, "authority_tree": TREE,
            "record_id": evidence["record_id"], "doi": evidence["doi"],
            "conceptdoi": evidence["conceptdoi"],
            "manifest_sha256": evidence["manifest_sha256"],
            "evidence_sha256": "a" * 64, "file_count": 65,
            "total_bytes": mirror.EXPECTED_TOTAL_BYTES,
        }
        second = {**first, "evidence_sha256": "b" * 64}
        environment = {
            mirror.MESH_TOKEN_ENV: "mesh-token-value-1234567890",
            "GITHUB_REPOSITORY": mirror.AUTHORITY,
            "GITHUB_REF": mirror.PUBLIC_REF,
            "GITHUB_SHA": HEAD,
            "QIKVRT_EVENT_CREATED": "true", "QIKVRT_EVENT_DELETED": "false",
            "QIKVRT_EVENT_FORCED": "false", "QIKVRT_EVENT_BEFORE": mirror.ZERO40,
            "QIKVRT_EVENT_AFTER": HEAD,
        }
        equality_commit, equality_tree = "8" * 40, "9" * 40
        overview_commit, overview_tree = "a" * 40, "b" * 40
        with (
            mock.patch.object(mirror, "verify_authority_gate", side_effect=[first, second]),
            mock.patch.object(mirror, "verify_guard_unchanged"),
            mock.patch.object(mirror, "verify_pair"),
            mock.patch.object(mirror, "verify_remote_integrity_anonymous"),
            mock.patch.object(mirror, "verify_pair_integrity_anonymous"),
            mock.patch.object(mirror, "ensure_create_only_ref"),
            mock.patch.object(mirror, "build_overview_files", return_value={}),
            mock.patch.object(mirror, "create_verified_stage_commit", side_effect=[(overview_commit, overview_tree), (equality_commit, equality_tree)]),
            mock.patch.object(mirror, "emit_frame"),
        ):
            with self.assertRaisesRegex(mirror.MirrorFinalizeError, "final anonymous public gate differs"):
                mirror.finalize(
                    transport=FakeTransport(), environment=environment,
                    manifest_raw=b"manifest", evidence_raw=b"evidence",
                    manifest=manifest, evidence=evidence, head=HEAD,
                )

    def test_effect_path_uses_zero_github_rest_reads(self) -> None:
        for function in (
            mirror.finalize,
            mirror.verify_authority_gate,
            mirror.verify_guard_unchanged,
            mirror.verify_pair,
            mirror.ensure_create_only_ref,
        ):
            source = inspect.getsource(function)
            self.assertNotIn("read_ref(", source)
            self.assertNotIn("read_commit(", source)
            self.assertNotIn("read_content(", source)
        self.assertLessEqual(mirror.MAX_ANONYMOUS_GITHUB_REST_REQUESTS, 8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
