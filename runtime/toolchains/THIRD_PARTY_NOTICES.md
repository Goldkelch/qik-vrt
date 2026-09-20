<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Third-party runtime notices

The following license texts apply to downloaded third-party runtime material.
They do not relicense QIK-VRT.

## GitHub CLI

MIT License

Copyright (c) 2019 GitHub Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## xml2rfc

BSD 3-Clause License

Copyright (c) 2022, IETF Trust
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors
   may be used to endorse or promote products derived from this software
   without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

## Locked Python dependencies

The xml2rfc environment also installs these exact third-party packages:

- certifi 2026.7.22
- charset-normalizer 3.4.9
- configargparse 1.7.5
- google-i18n-address 3.1.1
- idna 3.18
- intervaltree 3.2.1
- Jinja2 3.1.6
- lxml 6.1.1
- MarkupSafe 3.0.3
- natsort 8.4.0
- platformdirs 4.11.0
- pycountry 26.2.16
- pypdf 6.15.0
- PyYAML 6.0.3
- requests 2.34.2
- sortedcontainers 2.4.0
- urllib3 2.7.0
- wcwidth 0.8.2

Each package retains its own upstream copyright, license, notices, and warranty
terms. This QIK-VRT notice does not assign a license identifier where one was
not independently verified. The exact allowed wheel artifacts are bound by
SHA-256 in `requirements-xml2rfc-3.34.0.txt`; their embedded metadata and
license files remain the authoritative notices. A redistributor must inspect
and carry all notices required by those exact artifacts. Package metadata is
available from the Python Package Index at
`https://pypi.org/project/<package>/<version>/` and from each package's declared
upstream project links.

## Local multimedia reference

Qwen2.5-1.5B-Instruct and its official Q4_K_M GGUF conversion are supplied by
Qwen under Apache-2.0. The unchanged upstream bytes, revision and digest are
identified as `text_model` in `multimedia.lock.json`; the full license is
`LICENSES/Apache-2.0.txt`. Source:
https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/tree/dd26da440ef0330c47919d1ecae0966d24022222.
This upstream component does not change QIK-VRT's licensing model.

SmolVLM2-500M-Video-Instruct is supplied by Hugging Face and the pinned GGUF
conversion by ggml-org under Apache-2.0. The language and vision files are
identified in `multimedia.lock.json`; the full license is
`LICENSES/Apache-2.0.txt`. Source: https://huggingface.co/HuggingFaceTB/SmolVLM2-500M-Video-Instruct.

llama.cpp b6500 uses the MIT license in `llama-b6500-LICENSE.txt`. The verified
runner archive retains its own LICENSE and third-party notices for curl, httplib,
jsonhpp and linenoise. These files are retained when the cache is copied into the
container or ISO. No QIK-VRT license is applied to these upstream components.

The optional agent-browser 0.38.1 QA CLI is Apache-2.0, as declared by its exact
npm package. Its package lock is in `multimedia-browser/`. Downloaded Chromium
retains its separate upstream licensing; the browser check is not an ISO payload.

## Optional OIDC gateway

oauth2-proxy v7.15.4 is supplied under MIT by its upstream contributors. The
unchanged license is in `oauth2-proxy-v7.15.4-LICENSE.txt`; source and exact
archive identity are in `sso.lock.json`. The original archive remains cached
alongside the byte-verified executable. Its own dependency notices and licenses
remain applicable and must accompany redistribution. This optional upstream
component does not alter the QIK-VRT licensing model.
