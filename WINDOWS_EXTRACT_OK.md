# Windows extraction status

V1.2 is repackaged as a Windows-safe ZIP.

Checks applied:

- short root directory: `QIKVRT_ODU_V1_2_WINSAFE`
- ASCII-only internal paths
- no `\`, `:`, `*`, `?`, `"`, `<`, `>`, `|` characters in ZIP paths
- no Windows reserved path components such as `CON`, `PRN`, `AUX`, `NUL`, `COM1`, `LPT1`
- no trailing dot or trailing space in path components
- maximum internal ZIP path length below 120 characters
- no directory entries in the ZIP
- no duplicate entries
- no symlinks
- ZIP integrity tested

Status: `WINDOWS_EXTRACT_SAFE_PASS`
