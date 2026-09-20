#!/usr/bin/env python3
"""Bind and re-download complete distribution bytes; never infer product DONE."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import urllib.parse
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qikvrt_transfer_parts import (DEFAULT_PART_BYTES, MAX_MANIFEST_BYTES, MIB,
                                  PART_SUFFIX, describe, part_size, receive_file,
                                  transport_names, validate_file)

MANIFEST = 'qikvrt-distribution-manifest.json'
REQUIRED = (
    'qikvrt-megast-amd64.iso', 'qikvrt-megast-amd64.iso.sha256',
    'qikvrt-megast-vmlinuz', 'qikvrt-megast-initrd',
    'qikvrt-megast-filesystem.squashfs', 'qikvrt-netboot.json',
    'qikvrt-universal-terminal-amd64.docker.tar',
    'qikvrt-universal-terminal-amd64.docker.tar.sha256',
    'qikvrt-universal-terminal-image-inspect.json',
)

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def validate(manifest: dict, head: str, tree: str, max_part_bytes: int = DEFAULT_PART_BYTES) -> None:
    if not re.fullmatch(r'[0-9a-f]{40}', head) or not re.fullmatch(r'[0-9a-f]{40}', tree):
        raise ValueError('exact HEAD/TREE required')
    if manifest.get('schema') not in ('qikvrt_distribution_manifest_v1', 'qikvrt_distribution_manifest_v2'):
        raise ValueError('manifest schema mismatch')
    if manifest.get('source_head') != head or manifest.get('source_tree') != tree:
        raise ValueError('manifest subject mismatch')
    assets = manifest.get('assets')
    if not isinstance(assets, dict) or not set(REQUIRED) <= set(assets):
        raise ValueError('complete ISO/netboot/Docker payload required')
    v2 = manifest['schema'] == 'qikvrt_distribution_manifest_v2'
    limit = part_size(manifest.get('part_bytes')) if v2 else DEFAULT_PART_BYTES
    if limit > part_size(max_part_bytes):
        raise ValueError('sender part size exceeds receiver limit')
    for name, item in assets.items():
        if v2:
            validate_file(name, item, limit)
            continue
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,199}', name):
            raise ValueError('unsafe asset name')
        if not isinstance(item, dict) or type(item.get('bytes')) is not int or not 0 < item['bytes'] <= 2**32:
            raise ValueError('invalid asset byte count')
        if not re.fullmatch(r'[0-9a-f]{64}', str(item.get('sha256', ''))):
            raise ValueError('invalid asset hash')


def create(root: Path, head: str, tree: str, part_bytes: int = DEFAULT_PART_BYTES) -> dict:
    part_size(part_bytes)
    assets = {}
    for path in sorted(root.iterdir()):
        if path.name in (MANIFEST, MANIFEST + '.sha256', 'qikvrt-public-readback.json'):
            continue
        if PART_SUFFIX.search(path.name):
            continue
        if path.name.startswith('qikvrt-') or path.name in ('QIKVRT_BOOT.BIN', 'qikvrt_transfer_parts.py'):
            if path.is_symlink() or not path.is_file():
                raise ValueError('release asset must be a regular file: ' + path.name)
            if path.stat().st_size:
                assets[path.name] = describe(path, part_bytes)
    manifest = {'schema': 'qikvrt_distribution_manifest_v2', 'source_head': head, 'part_bytes': part_bytes,
                'source_tree': tree, 'assets': assets, 'acceptance_scope': 'artifact_bytes_only',
                'full_product_done': False, 'linux_distribution_done': False}
    validate(manifest, head, tree, part_bytes)
    path = root / MANIFEST
    path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    (root / (MANIFEST + '.sha256')).write_text(digest(path) + '  ' + MANIFEST + '\n', encoding='ascii')
    return manifest


def verify_local(root: Path, manifest: dict, head: str, tree: str, max_part_bytes: int = DEFAULT_PART_BYTES) -> None:
    validate(manifest, head, tree, max_part_bytes)
    for name, item in manifest['assets'].items():
        path = root / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size != item['bytes'] or digest(path) != item['sha256']:
            raise ValueError('asset integrity mismatch: ' + name)
        for part in item.get('parts', []):
            local = root / part['name']
            if not local.exists() and not local.is_symlink():
                local = root / (name + '.parts') / part['name']
            if local.is_symlink() or not local.is_file() or local.stat().st_size != part['bytes'] or digest(local) != part['sha256']:
                raise ValueError('transfer part integrity mismatch: ' + part['name'])


class HTTPSRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).scheme != 'https':
            raise ValueError('non-HTTPS redirect rejected')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(url: str, path: Path, expected_hash: str, expected_bytes: int | None = None) -> dict:
    if urllib.parse.urlsplit(url).scheme != 'https':
        raise ValueError('public HTTPS URL required')
    opener = urllib.request.build_opener(HTTPSRedirect())
    request = urllib.request.Request(url, headers={'User-Agent': 'qikvrt-public-readback/1', 'Cache-Control': 'no-cache'})
    limit = expected_bytes if expected_bytes is not None else MAX_MANIFEST_BYTES
    h, total = hashlib.sha256(), 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            with opener.open(request, timeout=60) as response:
                if response.status != 200:
                    raise ValueError('public response is not HTTP 200')
                for block in iter(lambda: response.read(1024 * 1024), b''):
                    total += len(block)
                    if total > limit:
                        raise ValueError('public payload exceeds expected size')
                    stream.write(block)
                    h.update(block)
            stream.flush()
            if h.hexdigest() != expected_hash or (expected_bytes is not None and total != expected_bytes):
                raise ValueError('public payload digest/size mismatch')
            stream.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    return {'url': url, 'http_status': 200, 'bytes': total, 'sha256': h.hexdigest()}


def readback(base: str, root: Path, manifest_hash: str, head: str, tree: str,
             max_part_bytes: int = DEFAULT_PART_BYTES) -> dict:
    if not re.fullmatch(r'[0-9a-f]{64}', manifest_hash):
        raise ValueError('trusted manifest hash required')
    root.mkdir(parents=True, exist_ok=True)
    observations = {MANIFEST: download(base.rstrip('/') + '/' + MANIFEST, root / MANIFEST, manifest_hash)}
    manifest = json.loads((root / MANIFEST).read_text(encoding='utf-8'))
    validate(manifest, head, tree, max_part_bytes)
    for name, item in manifest['assets'].items():
        if manifest['schema'] == 'qikvrt_distribution_manifest_v2':
            parts = receive_file(base, name, item, root, download, manifest['part_bytes'], fresh=True)
            observations[name] = {'transfer_observations': parts, 'bytes': item['bytes'],
                                  'sha256': item['sha256'], 'whole_file_verified': True}
        else:
            observations[name] = download(base.rstrip('/') + '/' + name, root / name, item['sha256'], item['bytes'])
        print('PUBLIC_PAYLOAD_VERIFIED ' + name, flush=True)
    verify_local(root, manifest, head, tree, max_part_bytes)
    result = {'schema': 'qikvrt_distribution_public_readback_v1', 'observed_at': dt.datetime.now(dt.timezone.utc).isoformat(),
              'source_head': head, 'source_tree': tree, 'manifest_sha256': manifest_hash,
              'anonymous': True, 'observations': observations, 'artifact_bytes_verified': True,
              'full_product_done': False, 'linux_distribution_done': False}
    (root / 'qikvrt-public-readback.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('manifest', 'verify', 'readback'))
    parser.add_argument('directory', type=Path)
    parser.add_argument('head')
    parser.add_argument('tree')
    parser.add_argument('--base-url')
    parser.add_argument('--manifest-sha256')
    parser.add_argument('--part-mib', type=int, default=2048, help='sender transfer part size')
    parser.add_argument('--max-part-mib', type=int, default=2048, help='receiver maximum transfer part size')
    args = parser.parse_args()
    if args.mode == 'manifest':
        create(args.directory, args.head, args.tree, args.part_mib * MIB)
        print(digest(args.directory / MANIFEST))
    elif args.mode == 'verify':
        verify_local(args.directory, json.loads((args.directory / MANIFEST).read_text()), args.head, args.tree,
                     args.max_part_mib * MIB)
    else:
        if not args.base_url or not args.manifest_sha256:
            parser.error('readback requires --base-url and --manifest-sha256')
        readback(args.base_url, args.directory, args.manifest_sha256, args.head, args.tree, args.max_part_mib * MIB)


if __name__ == '__main__':
    main()
