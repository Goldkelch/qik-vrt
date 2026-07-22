"""Create a single Lean source for independent WASM kernel checking."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORDER = [
    "Foundations.lean",
    "Iteration.lean",
    "Gates.lean",
    "Quantizability.lean",
    "Dimensions.lean",
    "Retrocausality.lean",
    "Claims.lean",
]


def main() -> None:
    chunks = ["import Std\n"]
    for name in ORDER:
        source = (ROOT / "QIKVRTFormalization" / name).read_text(encoding="utf-8")
        source = "\n".join(
            line for line in source.splitlines()
            if not line.startswith("import ")
        )
        chunks.append(f"\n/- SOURCE MODULE: {name} -/\n{source}\n")
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    (build / "All.lean").write_text("".join(chunks), encoding="utf-8")


if __name__ == "__main__":
    main()
