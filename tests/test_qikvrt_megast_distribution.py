import hashlib
import io
import json
import os
import pathlib
import runpy
import subprocess
import tempfile
import unittest
import zipfile
from unittest import mock
from urllib.parse import urlsplit

ROOT = pathlib.Path(__file__).resolve().parents[1]
BUILD = ROOT / "distribution/qikvrt-megast/build.sh"
SESSION = ROOT / "distribution/qikvrt-megast/qikvrt-megast-session.sh"
README = ROOT / "distribution/qikvrt-megast/README.md"
WORKFLOW = ROOT / ".github/workflows/qikvrt_megast_distribution_v1.yml"


class MegaSTDistributionContract(unittest.TestCase):
    def test_docker_context_excludes_generated_distribution_without_product_sources(self):
        # Run 35390074944 failed while Docker traversed the root-owned live-build
        # cache. Check the effective ignore file without rejecting additional
        # exclusions for credentials, Python caches or restored toolchain archives.
        ignore = ROOT / 'deploy/universal-terminal/Dockerfile.dockerignore'
        if not ignore.exists():
            ignore = ROOT / '.dockerignore'
        rules = [line.strip() for line in ignore.read_text().splitlines()
                 if line.strip() and not line.lstrip().startswith('#')]
        for generated in ('/.build/qikvrt-megast/', '/out/'):
            self.assertIn(generated, rules)
        for product in ('src', 'runtime', 'tools', 'deploy', '.git'):
            for spelling in (product, product + '/', '/' + product, '/' + product + '/'):
                self.assertNotIn(spelling, rules)
        for rule in rules:
            if rule.startswith('!'):
                retained = rule[1:].lstrip('/')
                self.assertFalse(retained.startswith(('.build/', 'out/')))

    def test_build_contract_is_fail_closed(self):
        text = BUILD.read_text()
        self.assertIn('set -eu', text)
        self.assertIn('effect_ack_done', text)
        self.assertIn('qikvrt-megast-amd64.iso.sha256', text)
        self.assertIn('BLOCKED: live-build produced no ISO', text)

    def test_megast_runtime_has_pinned_redistributable_emutos(self):
        lock = json.loads((ROOT / 'runtime/toolchains/emutos-1.4.lock.json').read_text())
        self.assertEqual(lock['version'], '1.4')
        self.assertEqual(lock['rom'], 'etos256de.img')
        self.assertEqual(lock['license'], 'GPL-2.0-or-later')
        self.assertEqual(lock['sha256'], 'aadd90cf0c99925d3f2943149dd51ee4deb6015aefe22ade4a5e6c04fb6f2e9d')
        build = BUILD.read_text()
        self.assertIn('EMUTOS_LOCK="$ROOT/runtime/toolchains/emutos-1.4.lock.json"', build)
        self.assertIn("sha256sum -c -", build)
        self.assertIn('len(data) != 256 * 1024', build)
        self.assertIn('/usr/share/hatari/tos.img', build)
        self.assertIn('"$WORK/config/includes.chroot/usr/share/qikvrt/emutos"', build)
        self.assertIn('"$WORK/config/includes.chroot/usr/share/hatari"', build)
        session = SESSION.read_text()
        self.assertIn('hatari --machine st --tos /usr/share/qikvrt/emutos/etos256de.img', session)
        self.assertNotIn('provide a legally usable TOS image', session)

    def _check_emutos_materialization(self, entries, *, expected_error=None, bad_digest=False):
        # Execute the real build prefix, not a second implementation of mkdir,
        # extraction or linking. Only network transport uses a local fixture.
        # Synthetic ROM bytes are never executed and do not witness a guest boot.
        boundary = '# Compile the real C90 corpus and the CPU-family bootstrap program into the guest.'
        build = BUILD.read_text()
        self.assertEqual(build.count(boundary), 1)
        lock_path = ROOT / 'runtime/toolchains/emutos-1.4.lock.json'
        original_lock = lock_path.read_bytes()
        lock = json.loads(original_lock)
        with tempfile.TemporaryDirectory(prefix='qikvrt emutos ') as temp:
            root = pathlib.Path(temp)
            staged_build = root / 'distribution/qikvrt-megast/build.sh'
            staged_build.parent.mkdir(parents=True)
            staged_build.write_text(build.split(boundary, 1)[0])
            archive_path = root / 'fixture.zip'
            with zipfile.ZipFile(archive_path, 'w') as archive:
                for name, payload in entries:
                    archive.writestr(name, payload)
            lock['sha256'] = ('0' * 64 if bad_digest else
                              hashlib.sha256(archive_path.read_bytes()).hexdigest())
            staged_lock = root / 'runtime/toolchains/emutos-1.4.lock.json'
            staged_lock.parent.mkdir(parents=True)
            staged_lock.write_text(json.dumps(lock))
            commands = root / 'commands'
            commands.mkdir()
            curl = commands / 'curl'
            curl.write_text(
                '#!/bin/sh\nset -eu\n'
                'while [ "$#" -gt 0 ]; do\n'
                '  if [ "$1" = -o ]; then\n'
                '    cp -- "$QIKVRT_TEST_EMUTOS_ARCHIVE" "$2"\n'
                '    exit 0\n'
                '  fi\n'
                '  shift\n'
                'done\nexit 64\n'
            )
            curl.chmod(0o755)
            work = root / 'clean work'
            out = root / 'output'
            self.assertFalse(work.exists())
            self.assertFalse(out.exists())
            result = subprocess.run(
                ['sh', str(staged_build)], cwd=root, capture_output=True,
                text=True, timeout=30,
                env=dict(os.environ, PATH=str(commands) + os.pathsep + os.environ['PATH'],
                         QIKVRT_TEST_EMUTOS_ARCHIVE=str(archive_path),
                         QIKVRT_MEGAST_WORK=str(work), QIKVRT_MEGAST_OUT=str(out),
                         QIKVRT_EXACT_SHA='0' * 40),
            )
            diagnostics = result.stdout + result.stderr
            guest = work / 'config/includes.chroot'
            rom = guest / 'usr/share/qikvrt/emutos' / lock['rom']
            link = guest / 'usr/share/hatari/tos.img'
            if expected_error is None:
                self.assertEqual(result.returncode, 0, diagnostics)
                self.assertEqual(rom.read_bytes(), entries[0][1])
                self.assertTrue(link.is_symlink())
                self.assertEqual(os.readlink(link), '../qikvrt/emutos/' + lock['rom'])
                self.assertEqual(link.resolve(strict=True), rom.resolve(strict=True))
                self.assertEqual(link.read_bytes(), entries[0][1])
            else:
                self.assertNotEqual(result.returncode, 0, diagnostics)
                self.assertIn(expected_error, diagnostics)
                self.assertFalse(rom.exists())
                self.assertFalse(link.is_symlink())
        self.assertEqual(lock_path.read_bytes(), original_lock)

    def test_emutos_materializes_rom_and_hatari_link_from_empty_workdir(self):
        self._check_emutos_materialization([
            ('emutos-1.4/etos256de.img', b'Q' * (256 * 1024)),
        ])

    def test_emutos_materialization_rejects_invalid_archives(self):
        payload = b'Q' * (256 * 1024)
        cases = [
            ('checksum', [('emutos/etos256de.img', payload)], 'FAILED', True),
            ('missing ROM', [('emutos/other.img', payload)],
             'BLOCKED: exact EmuTOS ROM not uniquely present', False),
            ('ambiguous ROM', [('one/etos256de.img', payload), ('two/etos256de.img', payload)],
             'BLOCKED: exact EmuTOS ROM not uniquely present', False),
            ('wrong size', [('emutos/etos256de.img', b'too short')],
             'BLOCKED: EmuTOS ROM size mismatch', False),
        ]
        for name, entries, error, bad_digest in cases:
            with self.subTest(case=name):
                self._check_emutos_materialization(
                    entries, expected_error=error, bad_digest=bad_digest,
                )

    def test_modern_compatibility_envelope_is_present(self):
        text = BUILD.read_text()
        for token in ('hatari', 'firefox-esr', 'flatpak', 'podman', 'xfce4'):
            self.assertIn(token, text)

    def test_live_build_uses_supported_security_and_updates_switches(self):
        text = BUILD.read_text()
        self.assertIn("lb config --help 2>&1 | grep -q -- '--security-suite'", text)
        self.assertIn('--security true --security-suite trixie-security', text)
        self.assertIn('debian-security trixie-security', text)
        self.assertIn('set -- "$@" --security false', text)
        self.assertIn("lb config --help 2>&1 | grep -q -- '--updates'", text)
        self.assertIn('set -- "$@" --updates true', text)

    def test_visual_shell_does_not_claim_atari_identity(self):
        text = SESSION.read_text()
        self.assertIn('Mega-ST/GEM-inspired', text)
        self.assertIn('does not claim binary or hardware identity', text)
        self.assertIn('effect_ack_done', text)

    def test_publication_waits_for_exact_main(self):
        text = WORKFLOW.read_text()
        self.assertIn("github.ref == 'refs/heads/main'", text)
        self.assertEqual(
            text.count('(cd out && sha256sum -c qikvrt-megast-amd64.iso.sha256)'),
            1,
        )
        self.assertIn('cd out\n          sha256sum -c qikvrt-megast-amd64.iso.sha256', text)
        self.assertIn('Read back published release metadata', text)

    def test_pull_request_build_is_literal_head_bound(self):
        text = WORKFLOW.read_text()
        subject = '${{ github.event.pull_request.head.sha || github.sha }}'
        self.assertEqual(text.count(f'ref: {subject}'), 2)
        self.assertIn(f'QIKVRT_EXACT_SHA: {subject}', text)
        self.assertIn(f'"source_sha": "{subject}"', text)
        self.assertIn(f'name: qikvrt-megast-{subject}', text)

    def test_workflow_pins_trixie_live_build_toolchain(self):
        text = WORKFLOW.read_text()
        self.assertNotIn('apt-get install -y live-build', text)
        self.assertIn('live-build_20250505+deb13u1_all.deb', text)
        self.assertIn(
            '58e09779881cbcc631c49ceb703413e0247a87db01823e597b2a1c40a2afd8f4',
            text,
        )
        self.assertIn('/tmp/live-build.deb | sha256sum -c -', text)
        self.assertIn('sudo dpkg -i /tmp/live-build.deb', text)
        self.assertIn('debian-archive-keyring_2025.1_all.deb', text)
        self.assertIn(
            '9ea7778e443144ca490668737a8ab22dd3e748bb99e805e22ec055abeb3c7fac',
            text,
        )
        self.assertIn('/tmp/debian-archive-keyring.deb | sha256sum -c -', text)
        self.assertIn('sudo dpkg -i /tmp/debian-archive-keyring.deb', text)

    def test_boot_witness_precedes_multi_user_and_qemu_binds_extracted_kernel(self):
        build = BUILD.read_text()
        workflow = WORKFLOW.read_text()
        self.assertIn("After=local-fs.target", build)
        self.assertIn("Before=multi-user.target", build)
        self.assertNotIn("After=multi-user.target", build)
        self.assertIn("-kernel out/qikvrt-megast-vmlinuz", workflow)
        self.assertIn("-initrd out/qikvrt-megast-initrd", workflow)
        self.assertIn("-append \"boot=live components", workflow)
        self.assertIn("-cdrom out/qikvrt-megast-amd64.iso", workflow)

    def test_terminal_definition_requires_download_readback(self):
        text = README.read_text()
        self.assertIn('stable release path', text)
        self.assertIn('independently read back after publication', text)
        self.assertIn('EFFECT_ACK_DONE', text)
        self.assertIn('Stay fail closed and keep future open', text)

    def test_pharo_image_uses_named_archive_without_changing_locked_bytes(self):
        # Runtime RED: distribution run 35212988079 received different bytes
        # from the mutable get-files alias. Retrieval changes, identity does not.
        lock = json.loads((ROOT / 'runtime/toolchains/pharo-13.lock.json').read_text())
        image = lock['image']
        url = urlsplit(image['url'])
        self.assertEqual(url.scheme, 'https')
        self.assertEqual(url.netloc, 'files.pharo.org')
        self.assertRegex(url.path, r'^/image/130/Pharo13\.0-SNAPSHOT\.build\.[0-9]+\.sha\.4f7563dfe5\.arch\.64bit\.zip$')
        self.assertEqual(image['file'], 'Pharo13.0-SNAPSHOT-64bit-4f7563dfe5.image')
        self.assertEqual(image['sha256'], '897668dd548864f74730065de3fa2b1f4b5d3636d4c7d14f91945f0a5ce22590')
        self.assertEqual(lock['vm']['sha256'], '80b106bbfd27f4db997e15831978836157043541c1e2b1e29fe3f10839bf78de')

    def test_pharo_vm_dependency_identity_remains_explicitly_pinned(self):
        # Fresh bounded probes established that the old expected VM bytes are no
        # longer served by either the named archive or the original stable alias.
        # This candidate explicitly pins the repeatedly reobserved named archive;
        # future upstream drift must still fail closed rather than self-repin.
        lock = json.loads((ROOT / 'runtime/toolchains/pharo-13.lock.json').read_text())
        vm = lock['vm']
        url = urlsplit(vm['url'])
        self.assertEqual(url.scheme, 'https')
        self.assertEqual(url.netloc, 'files.pharo.org')
        self.assertRegex(url.path, r'^/vm/pharo-spur64-headless/Linux-x86_64/PharoVM-v[0-9.]+\+[0-9]+\.[0-9a-f]+-Linux-x86_64-bin\.zip$')
        self.assertEqual(vm['sha256'], '80b106bbfd27f4db997e15831978836157043541c1e2b1e29fe3f10839bf78de')
        self.assertEqual(lock['version'], '13.1-4f7563dfe5-vm80b106bb')
        self.assertTrue(url.path.endswith('/PharoVM-v10.3.9+0.33e04bb-Linux-x86_64-bin.zip'))
        self.assertEqual(vm['file'], 'bin/pharo')

    def test_changed_upstream_bytes_cannot_install_or_change_lock(self):
        module = runpy.run_path(str(ROOT / 'tools/qikvrt_smalltalk.py'))
        lock_path = ROOT / 'runtime/toolchains/pharo-13.lock.json'
        original = lock_path.read_bytes()
        lock = json.loads(original)
        with tempfile.TemporaryDirectory() as temp:
            cache = pathlib.Path(temp)
            with mock.patch('platform.system', return_value='Linux'), mock.patch('platform.machine', return_value='x86_64'), mock.patch('urllib.request.urlopen', return_value=io.BytesIO(b'explicit-invalid-archive-fixture')) as fetch:
                with self.assertRaisesRegex(ValueError, 'downloaded archive digest mismatch'):
                    module['install'](cache, lock)
            self.assertEqual(fetch.call_count, 1)
            self.assertFalse(module['cache_path'](cache, lock).exists())
            self.assertEqual(list((cache / 'pharo').iterdir()), [])
        self.assertEqual(lock_path.read_bytes(), original)

    def test_pharo_lock_cache_and_distribution_have_one_version_authority(self):
        toolchains = ROOT / 'runtime/toolchains'
        lock = json.loads((toolchains / 'pharo-13.lock.json').read_text())
        rows = [line.split('\t') for line in (toolchains / 'TOOLCHAIN.lock.tsv').read_text().splitlines()
                if line.startswith('pharo\t')]
        self.assertEqual(len(rows), 2)
        for row in rows:
            kind = 'vm' if row[2] == 'linux-amd64-vm' else 'image'
            self.assertEqual(row[1], lock['version'])
            self.assertEqual(row[4], lock[kind]['sha256'])
        registry_bytes = (toolchains / 'CACHE_REGISTRY.json').read_bytes()
        registry = json.loads(registry_bytes)
        coverage = json.loads((toolchains / 'CACHE_COVERAGE.json').read_text())
        self.assertEqual(registry['components']['pharo']['version'], lock['version'])
        self.assertEqual(registry['components']['pharo']['cache_locations'],
                         ['.qikvrt/toolchains/pharo/' + lock['version']])
        self.assertEqual(coverage['lock_sha256'], hashlib.sha256((toolchains / 'TOOLCHAIN.lock.tsv').read_bytes()).hexdigest())
        self.assertEqual(coverage['registry_sha256'], hashlib.sha256(registry_bytes).hexdigest())
        pharo = [entry for entry in coverage['components'] if entry['component'] == 'pharo']
        self.assertEqual(len(pharo), 1)
        self.assertEqual(pharo[0]['version'], lock['version'])
        build = BUILD.read_text()
        self.assertIn('PHARO_VERSION=$(python3 -c', build)
        self.assertIn('"$ROOT/runtime/toolchains/pharo-13.lock.json"', build)
        self.assertIn('/pharo/$PHARO_VERSION/vm', build)
        self.assertNotIn('/pharo/13.1-', build)

    @staticmethod
    def archive_fixture(name, payload):
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w') as archive:
            archive.writestr(name, payload)
        return output.getvalue()

    def test_bad_vm_after_valid_image_cannot_install_or_damage_previous_cache(self):
        module = runpy.run_path(str(ROOT / 'tools/qikvrt_smalltalk.py'))
        lock_path = ROOT / 'runtime/toolchains/pharo-13.lock.json'
        original = lock_path.read_bytes()
        lock = json.loads(original)
        image = self.archive_fixture('fixture.image', b'synthetic image, never executed')
        lock['image']['sha256'] = hashlib.sha256(image).hexdigest()
        with tempfile.TemporaryDirectory() as temp:
            cache = pathlib.Path(temp)
            previous_lock = dict(lock, version='13.1-4f7563dfe5-vm33501fd6')
            previous = module['cache_path'](cache, previous_lock)
            previous.mkdir(parents=True)
            sentinel = previous / 'do-not-replace'
            sentinel.write_bytes(b'previous cache bytes')
            with mock.patch('platform.system', return_value='Linux'), mock.patch('platform.machine', return_value='x86_64'), mock.patch('urllib.request.urlopen', side_effect=[io.BytesIO(image), io.BytesIO(b'corrupt-vm-fixture')]) as fetch:
                with self.assertRaisesRegex(ValueError, 'vm: downloaded archive digest mismatch'):
                    module['install'](cache, lock)
            self.assertEqual(fetch.call_count, 2)
            self.assertFalse(module['cache_path'](cache, lock).exists())
            self.assertEqual(list((cache / 'pharo').iterdir()), [previous])
            self.assertEqual(sentinel.read_bytes(), b'previous cache bytes')
        self.assertEqual(lock_path.read_bytes(), original)

    def test_valid_local_archives_are_reverified_on_warm_path(self):
        module = runpy.run_path(str(ROOT / 'tools/qikvrt_smalltalk.py'))
        lock = json.loads((ROOT / 'runtime/toolchains/pharo-13.lock.json').read_text())
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            archives = root / 'archives'
            archives.mkdir()
            for kind, name in [('image', 'fixture.image'), ('vm', 'bin/pharo')]:
                data = self.archive_fixture(name, b'synthetic bytes, never executed')
                (archives / (kind + '.zip')).write_bytes(data)
                lock[kind]['sha256'] = hashlib.sha256(data).hexdigest()
            with mock.patch('platform.system', return_value='Linux'), mock.patch('platform.machine', return_value='x86_64'), mock.patch('urllib.request.urlopen', side_effect=AssertionError('local fixture must not fetch')):
                installed = module['install'](root / 'cache', lock, archives)
                self.assertEqual(module['verify'](root / 'cache', lock), installed)
                (installed / 'vm/bin/pharo').write_bytes(b'tampered extracted bytes')
                with self.assertRaisesRegex(ValueError, 'vm: extracted bytes changed'):
                    module['install'](root / 'cache', lock, archives)


if __name__ == '__main__':
    unittest.main()
