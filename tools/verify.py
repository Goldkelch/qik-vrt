from pathlib import Path
import hashlib, sys, re, json
ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PDF = '2382b5d4970559bc28649a6deb6797fe867fc70439140e4cf1c1e59964a37de6'
WIN_BAD_CHARS = set('<>:"|?*')
RESERVED = {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}

def sha256(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()

def fail(msg):
    print('BLOCK', msg)
    sys.exit(1)

required = [
    'assets/pdf/odu_proof.pdf', '.zenodo.json', 'CITATION.cff', 'MANIFEST.json',
    'GITHUB_DRY_RUN_VERIFY_ONLY.cmd', 'GITHUB_AUTH_PREFLIGHT_ONLY.cmd', 'GITHUB_ZENODO_UPLOAD_AND_PUBLISH.cmd',
    'GIT_INVOCATION_SELFTEST.cmd', 'POWERSHELL_PARSE_CHECK_ONLY.cmd',
    'tools/github_zenodo_release_publish.ps1', 'tools/git_invocation_selftest.ps1', 'tools/powershell_parse_check.ps1', 'tools/verify.py',
    'docs/v2_7_authz_preflight_fix.md',
    'qikvrt/acceptance_v2_7.json', 'qikvrt/report_v2_7.json', 'qikvrt/sandbox_git_local_execution_report_v2_7.json'
]
for rel in required:
    if not (ROOT/rel).is_file(): fail(f'missing required file: {rel}')
if sha256(ROOT/'assets/pdf/odu_proof.pdf') != EXPECTED_PDF: fail('PDF SHA256 mismatch')
try:
    rep=json.loads((ROOT/'qikvrt/sandbox_git_local_execution_report_v2_7.json').read_text(encoding='utf-8'))
    if rep.get('status')!='PASS': fail('sandbox local Git execution report v2.7 not PASS')
    if len(rep.get('commands',[])) < 7: fail('sandbox local Git execution report v2.7 too short')
except Exception as e:
    fail(f'bad sandbox local Git execution report v2.7: {e}')

for rel in ['ZENODO_UPLOAD_AND_PUBLISH.cmd','ZENODO_UPLOAD_DRAFT_ONLY.cmd','ZENODO_SANDBOX_DRAFT_ONLY.cmd','ZENODO_SANDBOX_UPLOAD_AND_PUBLISH.cmd','tools/zenodo_upload_pdf_publish.ps1']:
    if (ROOT/rel).exists(): fail(f'legacy Zenodo direct API executable remains: {rel}')

for p in list(ROOT.rglob('*.cmd')) + list(ROOT.rglob('*.ps1')):
    txt = p.read_text(errors='ignore')
    for pat in ['ZENODO_ACCESS_TOKEN','zenodo.org/api/deposit/depositions','/api/deposit/depositions']:
        if pat in txt: fail(f'direct Zenodo API/token pattern in executable: {p.relative_to(ROOT)}')
    for pat in ['Format-Volume','Clear-Content','Remove-Item']:
        if pat in txt: fail(f'destructive command pattern in executable: {p.relative_to(ROOT)}')
    if re.search(r"TrimStart\s*\(\s*['\"]\\\\['\"]", txt): fail(f'unsafe TrimStart escaped-backslash string pattern in executable: {p.relative_to(ROOT)}')
    if re.search(r"TrimStart\s*\(\s*['\"]/['\"]", txt): fail(f'unsafe TrimStart slash string pattern in executable: {p.relative_to(ROOT)}')
    if '/git/blobs' in txt or '/git/trees' in txt or '/git/commits' in txt: fail(f'Git Data API write endpoint remains in executable: {p.relative_to(ROOT)}')
    if p.suffix.lower()=='.cmd':
        low=' '+txt.lower()+' '
        for pat in [' del ', ' erase ', ' rmdir ', ' rd ']:
            if pat in low: fail(f'destructive cmd pattern in executable: {p.relative_to(ROOT)}')

ps = (ROOT/'tools/github_zenodo_release_publish.ps1').read_text(errors='ignore')
for forbidden in ['http.extraHeader=Authorization: Bearer','https://x-access-token:', 'Invoke-GitHubUploadfunction','function Invoke-GitSafe([string[]]$Args','param([string[]]$Args','[string[]]$Args','& git @Args','Invoke-GitSafe -Args @(','ProcessStartInfo','ArgumentList.Add','.ArgumentList']:
    if forbidden in ps: fail(f'forbidden PowerShell/Git pattern remains: {forbidden}')

if '.Trim()' in ps and '$stderr.Trim()' in ps: fail('direct stderr.Trim() null-unsafe pattern remains')
if 'Get-Content -LiteralPath $stdoutFile -Raw -ErrorAction SilentlyContinue }' in ps: fail('legacy null-unsafe stdout read block remains')
for required_frag in ["if ($null -eq $stdout) { $stdout = '' }", "if ($null -eq $stderr) { $stderr = '' }", "$stderrText = [string]$stderr", "$statusText = [string]$status"]:
    if required_frag not in ps: fail(f'missing V2.7 null-safe fragment: {required_frag}')


for required_frag in [
    'function Get-QikvrtObjProp', 'function Test-QikvrtRepoPushPermission', 'function Get-QikvrtRepoPermissionText',
    'Authenticated GitHub login:', 'Authenticated repository permission summary',
    'GitHub authorization preflight failed before local publish worktree creation',
    'has no push/write permission', 'GitHub repository write authorization preflight PASS'
]:
    if required_frag not in ps: fail(f'missing V2.7 authz preflight fragment: {required_frag}')

for required_frag in [
    'function Invoke-GitSafe', '[string[]]$GitArgs', 'Start-Process', 'RedirectStandardOutput', 'RedirectStandardError', 'ExitCode',
    'AuthPreflightOnly', 'Set-GitTransportAuthHeader', 'Get-GitAuthArgs', 'x-access-token:',
    'http.https://github.com/.extraheader=AUTHORIZATION: basic', 'credential.helper=', 'GCM_INTERACTIVE',
    'ls-remote', 'AUTH PREFLIGHT PASS', '$fetchArgs =', '$pushBranchArgs =', '$pushTagArgs =',
    'No GitHub Git-Blobs API used', 'AllowNotFound', '404 treated as expected absence', 'function Invoke-GitHubUpload([string]$UploadUrl'
]:
    if required_frag not in ps: fail(f'missing V2.7 auth-header publish fragment: {required_frag}')

selftest = (ROOT/'tools/git_invocation_selftest.ps1').read_text(errors='ignore')
if 'LocalGitSelfTestOnly' not in selftest: fail('git invocation selftest does not call LocalGitSelfTestOnly path')

for p in ROOT.rglob('*'):
    rel = str(p.relative_to(ROOT)).replace('\\','/')
    if len(rel) > 180: fail(f'path too long for conservative Windows-safe gate: {rel}')
    try: rel.encode('ascii')
    except UnicodeEncodeError: fail(f'non-ascii path: {rel}')
    for part in rel.split('/'):
        if any(c in WIN_BAD_CHARS for c in part): fail(f'windows-bad char in path: {rel}')
        stem = part.split('.')[0].upper().rstrip(' ')
        if stem in RESERVED: fail(f'reserved Windows name in path: {rel}')

sums = ROOT/'SHA256SUMS.txt'
if sums.exists():
    for line in sums.read_text().splitlines():
        if not line.strip(): continue
        sp=line.split(None,1)
        if len(sp)!=2: fail(f'bad SHA256SUMS line: {line}')
        digest, rel = sp[0].lower(), sp[1].strip()
        if rel.startswith('*'): rel=rel[1:]
        f=ROOT/rel
        if not f.exists(): fail(f'SHA256SUMS missing file: {rel}')
        if sha256(f)!=digest: fail(f'SHA256SUMS mismatch: {rel}')
print('PASS QIKVRT V2.7 GitHub authz preflight GitHub-only Zenodo integration package verified')
