"""Build a deterministic ZIP without dependency caches or volatile logs."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "release" / "QIKVRT_Formalization_v1.0_2026-07-22.zip"


def main() -> int:
    checksum_files = []
    for row in (ROOT / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        _, rel = row.split("  ", 1)
        checksum_files.append(ROOT / rel)
    receipts = [
        ROOT / "SHA256SUMS",
        ROOT / "build" / "lean-verification.json",
        ROOT / "build" / "negative-test-report.json",
        ROOT / "build" / "gate20-report.json",
        ROOT / "build" / "gate20-python-report.json",
        ROOT / "build" / "python-test-report.json",
    ]
    files = sorted({*checksum_files, *(p for p in receipts if p.exists())})
    OUT.parent.mkdir(exist_ok=True)
    prefix = "QIKVRT_Formalization_v1.0/"
    with ZipFile(OUT, "w", ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            info = ZipInfo(prefix + path.relative_to(ROOT).as_posix())
            info.date_time = (2026, 7, 22, 0, 0, 0)
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

