# Temporary branch-local bootstrap. Removed after repository-native materialization.
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from tools import qikvrt_anticipation

qikvrt_anticipation.materialize(root)
