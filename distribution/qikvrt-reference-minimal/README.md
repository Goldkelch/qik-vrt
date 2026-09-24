# QIK-VRT minimal reference Linux image

This directory is **Phase 1** of `REFERENCE_IMPLEMENTATION_FIRST`. It deliberately proves only the smallest Linux substrate needed for the later Atari/M68000, Universal Transputer, Universal Terminal and TEMDD stages.

## Acceptance predicate

```text
EXACT_SOURCE_HEAD_BOUND
AND EXACT_SOURCE_TREE_BOUND
AND BUILD_CONTRACT_BOUND
AND SOURCE_DATE_EPOCH_BOUND
AND SNAPSHOT_ARCHIVE_BOUND
AND BUILD_A_COMPLETED
AND BUILD_B_COMPLETED
AND SHA256(IMAGE_A) == SHA256(IMAGE_B)
AND BIOS_BOOT_WITNESS_OBSERVED
--------------------------------
REPRODUCIBLE_LINUX_IMAGE = TRUE
```

Both builds use separate work directories. Equality is byte equality of the final ISO, not merely equality of package lists or filesystem contents. A build receipt that does not hash the bytes being tested is rejected.

The Debian archive is addressed through the dated snapshot in `BUILD_CONTRACT.json`; normal rolling `stable`/`trixie` mirrors are not part of this contract. `SOURCE_DATE_EPOCH` is derived solely from the exact source commit timestamp and is exported into live-build and its child tools.

## Scope boundary

This phase does **not** claim Atari/M68000 execution, Transputer roundtrips, Universal Terminal operation, TEMDD runtime closure, public release, or `EFFECT_ACK_DONE`. Those are successor gates and must bind the exact accepted image digest produced here.

## Local build

The host needs the same toolchain used by CI: live-build 20250505+deb13u1, debootstrap, xorriso and squashfs-tools.

```sh
QIKVRT_REFERENCE_WORK=/tmp/qikvrt-ref-a \
QIKVRT_REFERENCE_OUT=/tmp/qikvrt-ref-a-out \
sudo -E ./distribution/qikvrt-reference-minimal/build.sh
```

Build a second time into different directories, then verify:

```sh
python3 distribution/qikvrt-reference-minimal/verify-rebuild.py \
  /tmp/qikvrt-ref-a-out/qikvrt-reference-linux-amd64.iso \
  /tmp/qikvrt-ref-a-out/qikvrt-reference-linux-build-receipt.json \
  /tmp/qikvrt-ref-b-out/qikvrt-reference-linux-amd64.iso \
  /tmp/qikvrt-ref-b-out/qikvrt-reference-linux-build-receipt.json \
  --output /tmp/qikvrt-reference-linux-rebuild-receipt.json
```
