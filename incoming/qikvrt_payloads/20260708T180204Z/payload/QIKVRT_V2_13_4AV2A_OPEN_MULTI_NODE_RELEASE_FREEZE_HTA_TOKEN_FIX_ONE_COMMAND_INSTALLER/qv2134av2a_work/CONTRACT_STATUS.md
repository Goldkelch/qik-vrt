# QIKVRT V2.13.4AV2A Open Multi-Node Release Freeze HTA Token Fix

Status: BUILT_FOR_OWNER_EXECUTION

Purpose: repair 4AV2 masked token prompt HTA syntax failure while retaining one-command release freeze, masked token input, no PowerShell, no .ps1, no Git command path, no embedded token.

Fixes:
- VISIBLE_TOKEN_PROMPT remains fixed.
- HTA_TOKEN_PROMPT_VBSCRIPT_INLINE_SUB_SYNTAX_ERROR fixed by replacing one-line VBScript HTA handlers with JavaScript HTA handlers.
- Release freeze logic retained.
- Existing tag no-move guard retained.
- Existing release no-overwrite guard retained.

Verification in sandbox:
- ZIP test PASS
- SHA256SUMS PASS
- JScript syntax PASS via node --check
- HTA prompt source contract PASS
- No .ps1 PASS
- No PowerShell execution marker PASS
- No Git command marker PASS
- No embedded token marker PASS

Boundaries:
- Windows native mshta runtime NOT_EXECUTED_IN_SANDBOX
- Remote GitHub release creation REQUIRES_OWNER_EXECUTION
- Full repository byte rehash NOT_EXECUTED_HERE
