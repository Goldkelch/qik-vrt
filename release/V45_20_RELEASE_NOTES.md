# QIKVRT V45.20 Release Notes

Persists the four QIK-VRT/quantum-gravity PDF documents and repairs the V45.19 release-create path.

## Repaired error class

`BLOCK_GH_RELEASE_VIEW_NATIVE_COMMAND_ERROR_BEFORE_RELEASE_CREATE`

V45.19 successfully committed, pushed `main`, and pushed the immutable tag, but `gh release view` wrote `release not found` to stderr. PowerShell raised a NativeCommandError before `gh release create` could execute. V45.20 uses a safe release-existence probe through `cmd.exe /d /c "gh release view <tag> >NUL 2>NUL"`; a missing release is treated as CONTINUE and then created.

No force-tag update. No asset clobber. Owner acceptance required before any remote effect.
