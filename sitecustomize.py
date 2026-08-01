# Temporary branch-local bootstrap. Removed after repository-native materialization.
from pathlib import Path

root = Path.cwd()
if (root / "anticipation" / "INPUT.json").is_file():
    from tools import qikvrt_anticipation

    qikvrt_anticipation.materialize(root)
