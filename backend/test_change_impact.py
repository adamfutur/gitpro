"""Unit tests for deterministic source-backed change impact mapping."""
import unittest
from services.change_impact import build_change_impact_graph


class ChangeImpactTests(unittest.TestCase):
    def test_typescript_relative_import_and_reverse_dependency(self):
        files = [
            {"path": "src/core.ts", "content": "export const answer = 42;"},
            {"path": "src/ui.tsx", "content": "import { answer } from './core'\nexport default answer"},
            {"path": "src/unrelated.ts", "content": "export const n = 7;"},
        ]
        graph = build_change_impact_graph([{"filename": "src/core.ts"}], files)
        self.assertEqual(graph["edges"], [
            {"from": "src/ui.tsx", "to": "src/core.ts", "type": "imports"}
        ])
        self.assertEqual({n["id"] for n in graph["nodes"]}, {"src/core.ts", "src/ui.tsx"})

    def test_python_absolute_import_under_backend_root(self):
        files = [
            {"path": "backend/services/helper.py", "content": "answer = 42"},
            {"path": "backend/routes/handler.py", "content": "from services.helper import answer"},
        ]
        graph = build_change_impact_graph([{"filename": "backend/services/helper.py"}], files)
        self.assertEqual(graph["edges"][0]["from"], "backend/routes/handler.py")

    def test_missing_files_are_reported_partial(self):
        graph = build_change_impact_graph([{"filename": "missing.py"}], [])
        self.assertTrue(graph["partial"])
        self.assertEqual(graph["changed_files_in_sample"], 0)

    def test_dynamic_external_imports_are_not_invented(self):
        files = [{"path": "src/app.ts", "content": "import React from 'react';"}]
        graph = build_change_impact_graph([{"filename": "src/app.ts"}], files)
        self.assertEqual(graph["edges"], [])

    def test_unrelated_source_not_mislabeled_as_dependency(self):
        files = [
            {"path": "src/a.py", "content": "x=1"},
            {"path": "src/b.py", "content": "x=2"},
        ]
        graph = build_change_impact_graph([{"filename": "src/a.py"}], files)
        self.assertEqual([n["id"] for n in graph["nodes"]], ["src/a.py"])

    def test_node_limit_prevents_unbounded_graph(self):
        files = [{"path": "src/target.py", "content": "x=1"}] + [
            {"path": f"src/dependent_{i}.py", "content": "from src.target import x"}
            for i in range(50)
        ]
        graph = build_change_impact_graph([{"filename": "src/target.py"}], files, max_nodes=10)
        self.assertLessEqual(len(graph["nodes"]), 10)
        self.assertTrue(graph["partial"])


if __name__ == "__main__":
    unittest.main()
