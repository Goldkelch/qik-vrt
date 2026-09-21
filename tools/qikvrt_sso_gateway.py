#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Explicit, loopback-only OIDC gateway for an existing personal noVNC terminal.

Authentication is delegated to the pinned oauth2-proxy and the operator's IdP.
No photograph, voice embedding, password or JWT is evaluated by an LLM here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import ssl
import stat
import subprocess
import sys
import tarfile
import tempfile
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.qikvrt_multimedia_runtime import check, digest, download

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'runtime/toolchains/sso.lock.json'
FIELDS = {'schema', 'issuer', 'client_id', 'origin', 'listen_port', 'novnc_port',
          'client_secret_file', 'cookie_secret_file', 'allowed_emails_file',
          'tls_cert_file', 'tls_key_file'}


def no_symlinks(path):
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('ABSOLUTE_CANONICAL_PATH_REQUIRED')
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError('SYMLINK_PATH_FORBIDDEN')


def private_file(value, label):
    if not isinstance(value, str):
        raise ValueError('FILE_PATH_REQUIRED: ' + label)
    path = Path(value)
    no_symlinks(path)
    if path.is_relative_to(ROOT):
        raise ValueError('AUTH_STATE_MUST_BE_OUTSIDE_REPOSITORY')
    info = path.stat()
    parent = path.parent.stat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or
            info.st_mode & 0o077 or parent.st_uid != os.getuid() or parent.st_mode & 0o077):
        raise ValueError('OWNER_ONLY_FILE_AND_DIRECTORY_REQUIRED: ' + label)
    if not 1 <= info.st_size <= 1024 * 1024:
        raise ValueError('AUTH_FILE_SIZE_OUTSIDE_CONTRACT: ' + label)
    return path


def https_url(value, label):
    if not isinstance(value, str) or any(ord(c) < 33 or ord(c) > 126 for c in value):
        raise ValueError('CANONICAL_HTTPS_URL_REQUIRED: ' + label)
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username is not None or
            parsed.password is not None or parsed.query or parsed.fragment or
            '%' in value or '\\' in value or parsed.port == 0):
        raise ValueError('CANONICAL_HTTPS_URL_REQUIRED: ' + label)
    return parsed


def validate(settings):
    if not isinstance(settings, dict) or set(settings) != FIELDS:
        raise ValueError('EXACT_SSO_SETTINGS_FIELDS_REQUIRED')
    if settings['schema'] != 'qikvrt_sso_gateway_v1':
        raise ValueError('UNSUPPORTED_SSO_SCHEMA')
    https_url(settings['issuer'], 'issuer')
    origin = https_url(settings['origin'], 'origin')
    if origin.path or origin.hostname not in ('localhost', '127.0.0.1'):
        raise ValueError('LOOPBACK_ORIGIN_WITHOUT_PATH_REQUIRED')
    for key in ('listen_port', 'novnc_port'):
        if type(settings[key]) is not int or not 1024 <= settings[key] <= 65535:
            raise ValueError('UNPRIVILEGED_PORT_REQUIRED: ' + key)
    if origin.port != settings['listen_port'] or settings['listen_port'] == settings['novnc_port']:
        raise ValueError('DISTINCT_PORTS_AND_MATCHING_ORIGIN_REQUIRED')
    if not isinstance(settings['client_id'], str) or not re.fullmatch(r'[A-Za-z0-9._:-]{1,128}', settings['client_id']):
        raise ValueError('INVALID_CLIENT_ID')
    files = {key: private_file(settings[key], key) for key in FIELDS if key.endswith('_file')}
    if len(set(files.values())) != len(files):
        raise ValueError('DISTINCT_AUTH_FILES_REQUIRED')
    if len(files['cookie_secret_file'].read_bytes()) != 32:
        raise ValueError('COOKIE_SECRET_REQUIRES_32_RAW_RANDOM_BYTES')
    secret = files['client_secret_file'].read_bytes()
    if not secret.strip() or len(secret) > 4096:
        raise ValueError('INVALID_CLIENT_SECRET_FILE')
    emails = files['allowed_emails_file'].read_text(encoding='utf-8').splitlines()
    if not 1 <= len(emails) <= 100 or len(set(emails)) != len(emails) or any(
            not re.fullmatch(r'[A-Za-z0-9.!#$&\x27+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+', e)
            for e in emails):
        raise ValueError('EXACT_NONEMPTY_EMAIL_ALLOWLIST_REQUIRED')
    return settings


def load_settings(path):
    private_file(str(path), 'settings')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('DUPLICATE_SETTINGS_KEY')
            result[key] = value
        return result
    return validate(json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique))


def configuration(settings):
    s = validate(settings)
    cookie_id = hashlib.sha256((s['client_id'] + s['origin']).encode()).hexdigest()[:16]
    options = {
        'provider': 'oidc', 'provider_display_name': 'QIK-VRT SSO',
        'oidc_issuer_url': s['issuer'], 'client_id': s['client_id'],
        'client_secret_file': s['client_secret_file'],
        'redirect_url': s['origin'] + '/oauth2/callback',
        'scope': 'openid profile email', 'code_challenge_method': 'S256',
        'insecure_oidc_skip_nonce': False, 'insecure_oidc_skip_issuer_verification': False,
        'insecure_oidc_allow_unverified_email': False, 'ssl_insecure_skip_verify': False,
        'authenticated_emails_file': s['allowed_emails_file'],
        'http_address': '', 'https_address': '127.0.0.1:' + str(s['listen_port']),
        'tls_cert_file': s['tls_cert_file'], 'tls_key_file': s['tls_key_file'],
        'tls_min_version': 'TLS1.2',
        'cookie_name': '__Host-qikvrt_sso_' + cookie_id, 'cookie_secure': True,
        'cookie_httponly': True, 'cookie_samesite': 'lax', 'cookie_path': '/',
        'cookie_secret_file': s['cookie_secret_file'], 'cookie_expire': '15m',
        'cookie_refresh': '0s', 'cookie_csrf_expire': '5m',
        'cookie_csrf_per_request': True, 'cookie_csrf_per_request_limit': 5,
        'session_cookie_minimal': True,
        'upstreams': ['http://127.0.0.1:' + str(s['novnc_port']) + '/'],
        'proxy_websockets': True, 'pass_host_header': True,
        'pass_access_token': False, 'pass_authorization_header': False,
        'set_authorization_header': False, 'pass_basic_auth': False,
        'pass_user_headers': False, 'skip_auth_strip_headers': True,
        'skip_jwt_bearer_tokens': False, 'reverse_proxy': False,
        'request_logging': False, 'auth_logging': False,
    }
    # JSON string/array/boolean literals are also valid for these TOML values.
    return ''.join(key + ' = ' + json.dumps(value) + '\n' for key, value in options.items())


def member_digest(archive, lock):
    with tarfile.open(archive, 'r:gz') as source:
        members = [m for m in source.getmembers() if m.name == lock['binary_member']]
        if len(members) != 1 or not members[0].isfile() or not 1 <= members[0].size <= 256 * 1024 * 1024:
            raise ValueError('EXACT_REGULAR_BINARY_MEMBER_REQUIRED')
        with source.extractfile(members[0]) as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify(directory, lock):
    no_symlinks(directory)
    archive = directory / lock['archive']['name']
    binary = directory / 'oauth2-proxy'
    check(archive, lock['archive'])
    if binary.is_symlink() or not binary.is_file() or digest(binary) != member_digest(archive, lock):
        raise ValueError('SSO_BINARY_ABSENT_OR_CHANGED')
    return binary


def clean_environment():
    # Environment variables otherwise override the strict generated configuration.
    return {key: value for key, value in os.environ.items() if not key.startswith('OAUTH2_PROXY_')}


def install(directory, lock):
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise ValueError('PINNED_GATEWAY_REQUIRES_LINUX_X86_64')
    no_symlinks(directory)
    download(directory, lock['archive'], lock['archive']['url'])
    binary = directory / 'oauth2-proxy'
    archive = directory / lock['archive']['name']
    member_digest(archive, lock)
    if not binary.exists() and not binary.is_symlink():
        with tempfile.NamedTemporaryFile(dir=directory, delete=False) as target:
            staged = Path(target.name)
            try:
                with tarfile.open(archive, 'r:gz') as source, source.extractfile(lock['binary_member']) as stream:
                    while block := stream.read(1024 * 1024):
                        target.write(block)
                target.flush(); os.fsync(target.fileno())
                staged.chmod(0o755)
                staged.replace(binary)
            finally:
                staged.unlink(missing_ok=True)
    binary = verify(directory, lock)
    version = subprocess.run([str(binary), '--version'], capture_output=True, text=True,
                             timeout=15, check=True, env=clean_environment())
    if not version.stdout.startswith('oauth2-proxy v' + lock['version'] + ' '):
        raise ValueError('SSO_VERSION_MISMATCH')
    print('VERIFIED oauth2-proxy ' + lock['version'], flush=True)


def run_gateway(binary, settings, check_only=False):
    config = configuration(settings)
    # Check key/certificate parsing and pairing locally before starting listeners.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(settings['tls_cert_file'], settings['tls_key_file'], password=lambda: b'')
    with tempfile.TemporaryDirectory(prefix='qikvrt-sso-') as temporary:
        path = Path(temporary) / 'oauth2-proxy.cfg'
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as output:
            output.write(config)
        command = [str(binary), '--config', str(path)]
        if check_only:
            # Check mode does not contact the IdP or establish a login.
            subprocess.run(command + ['--config-test'], check=True, timeout=30,
                           env=clean_environment())
            return
        child = subprocess.Popen(command, env=clean_environment())
        def stop(_signum, _frame):
            child.terminate()
        previous = signal.signal(signal.SIGTERM, stop)
        try:
            code = child.wait()
            if code:
                raise ValueError('SSO_GATEWAY_EXITED: ' + str(code))
        except KeyboardInterrupt:
            child.terminate()
        finally:
            signal.signal(signal.SIGTERM, previous)
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill(); child.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('install', 'verify', 'check', 'serve'))
    parser.add_argument('--cache-dir', type=Path, default=ROOT / '.qikvrt/toolchains/sso')
    parser.add_argument('--settings', type=Path)
    args = parser.parse_args()
    try:
        lock = json.loads(LOCK.read_text())
        directory = args.cache_dir.absolute()
        if args.command == 'install':
            install(directory, lock)
        else:
            binary = verify(directory, lock)
            if args.command == 'verify':
                print('VERIFIED locked SSO archive and executable; login NOT_TESTED')
            else:
                if args.settings is None:
                    raise ValueError('EXPLICIT_SETTINGS_REQUIRED')
                run_gateway(binary, load_settings(args.settings.absolute()), args.command == 'check')
        return 0
    except (ValueError, OSError, tarfile.TarError, subprocess.SubprocessError) as exc:
        print('HOLD: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
