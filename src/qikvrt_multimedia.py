#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Local, user-initiated multimedia proposals. Never an event-ledger writer."""
from __future__ import annotations

import base64
import hashlib
import hmac
import http.client
import json
import os
from pathlib import Path
import secrets
import shutil
import struct
import subprocess
import tempfile
import threading
import wave
from urllib.parse import urlsplit

ROOT = Path(os.environ.get('QIKVRT_MULTIMEDIA_ROOT', str(Path(__file__).resolve().parents[1])))
LOCK_PATH = ROOT / 'runtime/toolchains/multimedia.lock.json'
TOKEN = secrets.token_urlsafe(32)
SLOT = threading.BoundedSemaphore(1)
MAX_BODY = 18 * 1024 * 1024


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def model_port():
    port = int(os.environ.get('QIKVRT_MODEL_PORT', '8789'))
    if not 1024 <= port <= 65535:
        raise ValueError('INVALID_MODEL_PORT')
    return port


def provider(path, body=None, timeout=120):
    # Fixed loopback IP, no proxy environment, redirects, arbitrary URL or tools.
    connection = http.client.HTTPConnection('127.0.0.1', model_port(), timeout=timeout)
    try:
        connection.request('GET' if body is None else 'POST', path,
                           body=None if body is None else canonical(body),
                           headers={'Content-Type': 'application/json'})
        response = connection.getresponse()
        raw = response.read(128 * 1024 + 1)
        if response.status != 200 or len(raw) > 128 * 1024:
            raise ValueError('MODEL_RESPONSE_UNAVAILABLE_OR_TOO_LARGE')
        return json.loads(raw)
    finally:
        connection.close()


def image_dimensions(raw, mime):
    if mime == 'image/png' and raw[:8] == b'\x89PNG\r\n\x1a\n' and raw[12:16] == b'IHDR' and len(raw) >= 24:
        return struct.unpack('>II', raw[16:24])
    if mime == 'image/jpeg' and raw[:2] == b'\xff\xd8':
        pos = 2
        while pos + 4 <= len(raw):
            if raw[pos] != 255:
                break
            while pos < len(raw) and raw[pos] == 255:
                pos += 1
            if pos + 3 > len(raw):
                break
            marker = raw[pos]
            size = int.from_bytes(raw[pos + 1:pos + 3], 'big')
            if size < 2 or pos + 1 + size > len(raw):
                break
            if marker in (0xc0, 0xc1, 0xc2) and size >= 8:
                height, width = struct.unpack('>HH', raw[pos + 4:pos + 8])
                return width, height
            if marker == 0xda:
                break
            pos += 1 + size
    raise ValueError('INVALID_IMAGE_HEADER')


def generation(body, lock):
    if not isinstance(body, dict) or set(body) - {'prompt', 'images'}:
        raise ValueError('PROMPT_AND_IMAGES_ONLY')
    prompt, images = body.get('prompt'), body.get('images', [])
    limits = lock['limits']
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > limits['prompt_characters']:
        raise ValueError('PROMPT_SIZE')
    if not isinstance(images, list) or len(images) > limits['images']:
        raise ValueError('IMAGE_COUNT')
    content = [{'type': 'text', 'text': prompt}]
    sources = []
    for entry in images:
        if not isinstance(entry, dict) or set(entry) != {'data', 'label'} or not isinstance(entry['label'], str) or len(entry['label']) > 160:
            raise ValueError('IMAGE_FIELDS')
        uri = entry['data']
        if not isinstance(uri, str) or len(uri) > 4 * limits['image_bytes'] // 3 + 100:
            raise ValueError('IMAGE_SIZE')
        header, encoded = uri.split(',', 1)
        if header not in ('data:image/jpeg;base64', 'data:image/png;base64'):
            raise ValueError('LOCAL_JPEG_OR_PNG_REQUIRED')
        raw = base64.b64decode(encoded, validate=True)
        if not 0 < len(raw) <= limits['image_bytes']:
            raise ValueError('IMAGE_SIZE')
        mime = header[5:].split(';')[0]
        width, height = image_dimensions(raw, mime)
        if not 0 < width <= limits['image_dimension'] or not 0 < height <= limits['image_dimension']:
            raise ValueError('IMAGE_DIMENSIONS')
        sources.append({'label': entry['label'], 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), 'width': width, 'height': height})
        content.extend([{'type': 'text', 'text': entry['label']}, {'type': 'image_url', 'image_url': {'url': uri}}])
    result = provider('/v1/chat/completions', {
        'model': lock['model_id'], 'messages': [{'role': 'user', 'content': content}],
        'max_tokens': limits['output_tokens'], 'temperature': 0, 'stream': False})
    if result.get('model') != lock['model_id']:
        raise ValueError('MODEL_ID_MISMATCH')
    answer = result['choices'][0]['message']['content']
    if not isinstance(answer, str) or not answer.strip() or len(answer) > 20000:
        raise ValueError('INVALID_MODEL_TEXT')
    return {'schema': 'qikvrt_multimedia_proposal_v1', 'state': 'UNVERIFIED_PROPOSAL',
            'model': lock['model_id'], 'model_identity': 'LOCAL_PROVIDER_REPORTED_ALIAS',
            'lock_sha256': hashlib.sha256(LOCK_PATH.read_bytes()).hexdigest(),
            'input_sha256': hashlib.sha256(canonical(body)).hexdigest(),
            'output_sha256': hashlib.sha256(answer.encode()).hexdigest(),
            'images': sources, 'text': answer, 'finish_reason': result['choices'][0].get('finish_reason'),
            'audio_included': False, 'ordinary_release': False, 'effect_ack_done': False, 'tools_executed': []}


def audio_paths():
    model = Path(os.environ.get('QIKVRT_AUDIO_MODEL_DIR', str(Path.home() / '.local/share/transcribe-audio-offline/model')))
    script = ROOT / 'tools/offline-audio-transcription/src/transcribe.cjs'
    available = bool(shutil.which('node') and shutil.which('ffmpeg') and shutil.which('ffprobe')
                     and (script.parents[1] / 'node_modules/sherpa-onnx-node').exists()
                     and all((model / f).is_file() for f in ('base-encoder.int8.onnx', 'base-decoder.int8.onnx', 'base-tokens.txt')))
    return script, model, available


def transcription(body):
    if not isinstance(body, dict) or set(body) != {'data', 'language'} or body['language'] not in ('de', 'en'):
        raise ValueError('AUDIO_FIELDS_OR_LANGUAGE')
    if not isinstance(body['data'], str):
        raise ValueError('AUDIO_DATA')
    raw = base64.b64decode(body['data'], validate=True)
    if not 0 < len(raw) <= 12 * 1024 * 1024:
        raise ValueError('AUDIO_SIZE_12_MIB')
    script, model, available = audio_paths()
    if not available:
        raise ValueError('OFFLINE_AUDIO_RUNTIME_NOT_INSTALLED')
    with tempfile.TemporaryDirectory(prefix='qikvrt-media-') as temporary:
        directory = Path(temporary)
        # Decode only bytes supplied through stdin. No playlist can open a file,
        # URL or nested protocol. Pass a generated PCM WAV to the reused ASR tool.
        decoded = subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-protocol_whitelist', 'pipe',
                                  '-i', 'pipe:0', '-map', '0:a:0', '-ac', '1', '-ar', '16000',
                                  '-t', '121', '-f', 's16le', 'pipe:1'], input=raw,
                                 capture_output=True, timeout=30, check=True)
        pcm = decoded.stdout
        duration = len(pcm) / 32000
        if not 0 < duration <= 120 or len(pcm) % 2:
            raise ValueError('AUDIO_DURATION_120_SECONDS')
        if not any(pcm):
            return {'state': 'NO_AUDIO_ENERGY', 'text': '', 'duration_seconds': duration,
                    'input_sha256': hashlib.sha256(raw).hexdigest(),
                    'engine': 'bounded PCM decoder; Whisper not invoked for exact digital silence',
                    'effect_ack_done': False, 'model_generation_performed': False}
        input_path = directory / 'input.wav'
        with wave.open(str(input_path), 'wb') as writer:
            writer.setnchannels(1); writer.setsampwidth(2); writer.setframerate(16000); writer.writeframes(pcm)
        subprocess.run(['node', str(script), '--input', str(input_path), '--output-dir', str(directory / 'out'),
                        '--model-dir', str(model), '--language', body['language']], capture_output=True, timeout=180, check=True)
        transcript = (directory / 'out/input.transcript.txt').read_text()
        if len(transcript) > 12000:
            raise ValueError('TRANSCRIPT_TOO_LARGE')
        return {'state': 'UNVERIFIED_TRANSCRIPT', 'text': transcript,
                'input_sha256': hashlib.sha256(raw).hexdigest(), 'duration_seconds': duration,
                'engine': 'repository whisper-base-int8 / sherpa-onnx-node 1.13.4',
                'effect_ack_done': False, 'model_generation_performed': False}


def reply(handler, code, value, media='application/json; charset=utf-8'):
    payload = value if isinstance(value, bytes) else canonical(value)
    handler.send_response(code)
    for name, value in {'Content-Type': media, 'Content-Length': str(len(payload)), 'Cache-Control': 'no-store',
                        'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer',
                        'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' blob: data:; media-src blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"}.items():
        handler.send_header(name, value)
    handler.end_headers()
    handler.wfile.write(payload)


def handle(handler):
    """Return true only for our routes; existing Effect-ACK semantics stay separate."""
    path = urlsplit(handler.path).path
    if path != '/multimedia' and not path.startswith('/multimedia/') and not path.startswith('/api/multimedia/'):
        return False
    handler.close_connection = True  # reject unread/pipelined bodies after any early error
    host = handler.headers.get('Host', '')
    local = {f'127.0.0.1:{handler.server.server_port}', f'localhost:{handler.server.server_port}'}
    if host not in local or handler.client_address[0] != '127.0.0.1' or handler.headers.get('Origin') not in (None, 'http://' + host):
        reply(handler, 403, {'state': 'HOLD', 'reason': 'LOCAL_SAME_ORIGIN_REQUIRED'})
        return True
    acquired = False
    try:
        lock = json.loads(LOCK_PATH.read_text())
        assets = {'/multimedia': ('index.html', 'text/html; charset=utf-8'), '/multimedia/': ('index.html', 'text/html; charset=utf-8'),
                  '/multimedia/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/multimedia/style.css': ('style.css', 'text/css; charset=utf-8')}
        if handler.command == 'GET' and path in assets:
            filename, mime = assets[path]
            reply(handler, 200, (ROOT / 'docs/terminal/multimedia' / filename).read_bytes(), mime)
        elif handler.command == 'GET' and path == '/api/multimedia/status':
            ready = False
            try:
                ready = provider('/health', timeout=2).get('status') == 'ok' and any(
                    m.get('id') == lock['model_id'] for m in provider('/v1/models', timeout=2).get('data', []))
            except (OSError, ValueError, http.client.HTTPException):
                pass
            reply(handler, 200, {'model': lock['model_id'], 'ready': ready, 'audio_ready': audio_paths()[2],
                                'csrf': TOKEN, 'limits': lock['limits'], 'effect_ack_done': False})
        elif handler.command == 'POST' and path in ('/api/multimedia/generate', '/api/multimedia/transcribe'):
            if handler.headers.get('Origin') != 'http://' + host or not hmac.compare_digest(handler.headers.get('X-QIKVRT-Media-Token', ''), TOKEN):
                reply(handler, 403, {'state': 'HOLD', 'reason': 'LOCAL_PAGE_TOKEN_REQUIRED'})
                return True
            if handler.headers.get('Transfer-Encoding') or len(handler.headers.get_all('Content-Length', [])) != 1:
                raise ValueError('ONE_CONTENT_LENGTH_REQUIRED')
            length = int(handler.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_BODY or handler.headers.get('Content-Type') != 'application/json':
                raise ValueError('BOUNDED_JSON_REQUIRED')
            if not SLOT.acquire(blocking=False):
                reply(handler, 429, {'state': 'HOLD', 'reason': 'MODEL_BUSY'})
                return True
            acquired = True
            handler.connection.settimeout(15)
            raw = handler.rfile.read(length)
            if len(raw) != length:
                raise ValueError('INCOMPLETE_INPUT')
            body = json.loads(raw)
            reply(handler, 200, generation(body, lock) if path.endswith('/generate') else transcription(body))
        else:
            reply(handler, 404, {'state': 'HOLD', 'reason': 'UNKNOWN_MEDIA_ROUTE'})
    except (OSError, ValueError, KeyError, IndexError, TypeError, RecursionError, http.client.HTTPException, subprocess.SubprocessError) as exc:
        # Do not echo a provider response, prompt, file name or audio in errors/logs.
        reason = str(exc) if isinstance(exc, ValueError) and str(exc).replace('_', '').isalnum() else 'MEDIA_RUNTIME_UNAVAILABLE_OR_INVALID_INPUT'
        reply(handler, 422, {'state': 'HOLD', 'reason': reason, 'effect_ack_done': False})
    finally:
        if acquired:
            SLOT.release()
    return True
