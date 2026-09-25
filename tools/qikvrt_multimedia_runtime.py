#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Install/verify the pinned local CPU model. No prompt is sent to a network API."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'runtime/toolchains/multimedia.lock.json'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check(path, entry):
    if path.is_symlink() or not path.is_file() or path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']:
        raise ValueError('ABSENT_OR_CHANGED: ' + path.name)


def download(directory, entry, url):
    path = directory / entry['name']
    if path.exists():
        check(path, entry)
        return
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=directory, delete=False) as output:
        temporary = Path(output.name)
        try:
            print('DOWNLOAD ' + entry['name'], flush=True)
            with urllib.request.urlopen(url, timeout=45) as response:
                size = 0
                while block := response.read(1024 * 1024):
                    size += len(block)
                    if size > entry['bytes']:
                        raise ValueError('DOWNLOAD_EXCEEDS_LOCK')
                    output.write(block)
            output.flush()
            os.fsync(output.fileno())
            check(temporary, entry)
            temporary.chmod(0o644)  # public model/runtime bytes; readable by service user
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def verify(directory, lock):
    archive = directory / lock['runner']['name']
    check(archive, lock['runner'])
    for entry in [*lock['models'], lock['text_model']]:
        check(directory / entry['name'], entry)
    # Compare every extracted file against the locked archive, not a mutable receipt.
    with zipfile.ZipFile(archive) as source:
        for entry in source.infolist():
            if entry.is_dir():
                continue
            target = directory / 'runner' / entry.filename
            if target.is_symlink() or not target.is_file() or target.read_bytes() != source.read(entry):
                raise ValueError('RUNNER_BYTES_CHANGED: ' + entry.filename)
    binaries = list((directory / 'runner').rglob('llama-server'))
    if len(binaries) != 1:
        raise ValueError('EXACTLY_ONE_LLAMA_SERVER_REQUIRED')
    return binaries[0]


def install(directory, lock):
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise ValueError('PINNED_RUNNER_REQUIRES_LINUX_X86_64')
    download(directory, lock['runner'], lock['runner']['url'])
    base = 'https://huggingface.co/ggml-org/SmolVLM2-500M-Video-Instruct-GGUF/resolve/' + lock['model_revision'] + '/'
    for entry in lock['models']:
        download(directory, entry, base + entry['name'])
    download(directory, lock['text_model'], lock['text_model']['url'])
    if not (directory / 'runner').exists():
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            stage = Path(temporary) / 'runner'
            stage.mkdir()
            with zipfile.ZipFile(directory / lock['runner']['name']) as source:
                for entry in source.infolist():
                    target = stage / entry.filename
                    if not target.resolve().is_relative_to(stage.resolve()) or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                        raise ValueError('UNSAFE_ARCHIVE_MEMBER')
                    source.extract(entry, stage)
                    if not entry.is_dir():
                        target.chmod(0o755 if entry.filename.endswith('llama-server') or '.so' in entry.filename else 0o644)
            stage.rename(directory / 'runner')
    binary = verify(directory, lock)
    result = subprocess.run([str(binary), '--version'], capture_output=True, text=True, timeout=15, check=True)
    if '6500' not in result.stdout + result.stderr:
        raise ValueError('RUNNER_VERSION_MISMATCH')
    print('VERIFIED ' + lock['model_id'], flush=True)


def serve(binary, directory, lock, vision_port, text_port):
    """One supervised service; stop both providers if either exits or on shutdown."""
    if vision_port == text_port:
        raise ValueError('DISTINCT_MODEL_PORTS_REQUIRED')
    common = [str(binary), '--host', '127.0.0.1', '-c', '8192', '-np', '1',
              '-t', '4', '-ngl', '0', '--no-webui']
    commands = [
        common + ['--port', str(vision_port), '--alias', lock['model_id'],
                  '-m', str(directory / lock['models'][0]['name']),
                  '--mmproj', str(directory / lock['models'][1]['name'])],
        common + ['--port', str(text_port), '--alias', lock['text_model']['model_id'],
                  '-m', str(directory / lock['text_model']['name'])]]
    children = []
    def stop(_signum, _frame):
        raise KeyboardInterrupt
    previous = signal.signal(signal.SIGTERM, stop)
    try:
        for command in commands:
            children.append(subprocess.Popen(command))
        while all(child.poll() is None for child in children):
            time.sleep(.25)
        raise ValueError('MODEL_CHILD_EXITED')
    except KeyboardInterrupt:
        return
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        signal.signal(signal.SIGTERM, previous)


def export_context(destination):
    """Carry the same bounded public source corpus into the existing ISO layout."""
    sys.path.insert(0, str(ROOT / 'src'))
    import qikvrt_multimedia as media
    if destination.is_symlink() or not destination.is_dir():
        raise ValueError('CONTEXT_DESTINATION_DIRECTORY_REQUIRED')
    manifest, _ = media.repository_manifest()
    selected = [entry for entry in manifest['files'] if media.context_entry(entry)]
    paths = [entry['path'] for entry in selected] + [
        'REPOSITORY_FILE_MANIFEST.json', 'REPOSITORY_FILE_MANIFEST.json.sha256',
        'tools/qikvrt_integrity.py', 'tools/qikvrt_subprocess.py']
    for relative in paths:
        target = destination / relative
        if any(part.is_symlink() for part in (target, *target.parents)):
            raise ValueError('CONTEXT_DESTINATION_SYMLINK')
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = media._regular_file_bytes(ROOT, relative, max_bytes=8 * 1024 * 1024)
        entry = next((item for item in selected if item['path'] == relative), None)
        if entry is not None and hashlib.sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError('CONTEXT_SOURCE_CHANGED')
        target.write_bytes(raw)
        target.chmod(0o644)
    print(json.dumps({'state': 'CONTEXT_EXPORTED', 'files': len(paths),
                      'scope': 'public bounded retrieval corpus, not complete repository',
                      'effect_ack_done': False}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('install', 'verify', 'serve', 'export-context'))
    parser.add_argument('--cache-dir', default=os.environ.get('QIKVRT_MULTIMEDIA_CACHE', str(ROOT / '.qikvrt/toolchains/multimedia')))
    parser.add_argument('--port', type=int, default=int(os.environ.get('QIKVRT_MODEL_PORT', '8789')))
    parser.add_argument('--text-port', type=int, default=int(os.environ.get('QIKVRT_TEXT_MODEL_PORT', '8790')))
    parser.add_argument('--output-dir')
    args = parser.parse_args()
    try:
        if args.operation == 'export-context':
            if not args.output_dir:
                raise ValueError('OUTPUT_DIR_REQUIRED')
            export_context(Path(args.output_dir))
            return 0
        if not all(1024 <= port <= 65535 for port in (args.port, args.text_port)):
            raise ValueError('INVALID_PORT')
        directory = Path(args.cache_dir).absolute()
        if any(p.is_symlink() for p in (directory, *directory.parents)):
            raise ValueError('CACHE_SYMLINK_DENIED')
        lock = json.loads(LOCK.read_text())
        if args.operation == 'install':
            install(directory, lock)
        binary = verify(directory, lock)
        if args.operation == 'serve':
            print('SERVE loopback model; no repository execution authority', flush=True)
            serve(binary, directory, lock, args.port, args.text_port)
        print(json.dumps({'state': 'VERIFIED_LOCAL_BYTES', 'model': lock['model_id'],
                          'text_model': lock['text_model']['model_id'], 'lock_sha256': digest(LOCK), 'effect_ack_done': False}))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        print('HOLD ' + str(exc))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
