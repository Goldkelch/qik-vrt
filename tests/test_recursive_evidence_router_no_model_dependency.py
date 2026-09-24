import ast
import pathlib
import unittest


class NoExternalCognitionDependencyTest(unittest.TestCase):
    def test_router_has_only_standard_library_imports(self):
        path = pathlib.Path(__file__).resolve().parents[1] / "src" / "qikvrt" / "recursive_evidence_router.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".")[0])
        self.assertLessEqual(roots, {"__future__", "dataclasses", "enum", "heapq", "typing"})


if __name__ == "__main__":
    unittest.main()
