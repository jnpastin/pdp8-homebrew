"""Tests for artifact_changes: material, moved, renamed, added, and removed entries."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import artifact_changes as C  # noqa: E402


def case(identifier, uops, line=10, path="docs/a.md", **extra):
    return {"id": identifier, "source": {"path": path, "line": line}, "micro_operations": uops, **extra}


class StripLocationsTests(unittest.TestCase):
    def test_removes_line_keys_at_any_depth(self):
        value = {"a": 1, "line": 3, "source": {"path": "p", "line": 4},
                 "list": [{"source_line": 5, "b": 2}]}
        self.assertEqual(C.strip_locations(value),
                         {"a": 1, "source": {"path": "p"}, "list": [{"b": 2}]})


class CompareEntriesTests(unittest.TestCase):
    def compare(self, old, new):
        return C.compare_entries({c["id"]: c for c in old}, {c["id"]: c for c in new})

    def test_unchanged_entries_are_omitted(self):
        self.assertEqual(self.compare([case("a", ["X"])], [case("a", ["X"])]), [])

    def test_a_shifted_line_is_moved(self):
        changes = self.compare([case("a", ["X"], line=10)], [case("a", ["X"], line=14)])
        self.assertEqual(changes, [C.EntryChange(C.MOVED, "a")])

    def test_changed_content_is_material(self):
        changes = self.compare([case("a", ["X"], line=10)], [case("a", ["Y"], line=14)])
        self.assertEqual(changes, [C.EntryChange(C.MATERIAL, "a")])

    def test_a_changed_path_is_material(self):
        changes = self.compare([case("a", ["X"])], [case("a", ["X"], path="docs/b.md")])
        self.assertEqual([c.kind for c in changes], [C.MATERIAL])

    def test_added_and_removed(self):
        changes = self.compare([case("a", ["X"]), case("b", ["Y"])], [case("a", ["X"]), case("c", ["Z"])])
        self.assertEqual(changes, [C.EntryChange(C.ADDED, "c"), C.EntryChange(C.REMOVED, "b")])

    def test_same_content_under_a_new_identifier_is_a_rename(self):
        old = [case("mri:3.1", ["X"], line=30, title="3.1 AND")]
        new = [case("mri:3.2", ["X"], line=52, title="3.2 AND")]
        self.assertEqual(self.compare(old, new), [C.EntryChange(C.RENAMED, "mri:3.2", "mri:3.1")])

    def test_an_ambiguous_rename_is_added_and_removed(self):
        old = [case("a", ["X"]), case("b", ["X"])]
        new = [case("c", ["X"])]
        kinds = sorted(c.kind for c in self.compare(old, new))
        self.assertEqual(kinds, [C.ADDED, C.REMOVED, C.REMOVED])


class CompareArtifactsTests(unittest.TestCase):
    def test_entry_lists_are_compared_by_identifier(self):
        old = {"format_version": 1, "cases": [case("a", ["X"], line=1), case("b", ["Y"])]}
        new = {"format_version": 1, "cases": [case("a", ["X"], line=2), case("b", ["Z"])]}
        self.assertEqual(C.compare_artifacts(old, new),
                         [C.EntryChange(C.MOVED, "cases:a"), C.EntryChange(C.MATERIAL, "cases:b")])

    def test_other_values_are_one_entry(self):
        old = {"sources": [{"document": "d", "line": 1}], "version": 1}
        new = {"sources": [{"document": "d", "line": 9}], "version": 2}
        self.assertEqual(C.compare_artifacts(old, new),
                         [C.EntryChange(C.MOVED, "sources"), C.EntryChange(C.MATERIAL, "version")])

    def test_symbolic_case_identifier(self):
        old = {"cases": [{"execution_case_id": "x", "source": {"path": "p", "line": 1}}]}
        new = {"cases": [{"execution_case_id": "x", "source": {"path": "p", "line": 2}}]}
        self.assertEqual(C.compare_artifacts(old, new), [C.EntryChange(C.MOVED, "cases:x")])

    def test_new_artifact(self):
        self.assertEqual([c.kind for c in C.compare_artifacts(None, {"a": 1})], [C.ADDED])


class DescribeTests(unittest.TestCase):
    def test_counts_in_a_fixed_order(self):
        changes = [C.EntryChange(C.MOVED, "a"), C.EntryChange(C.MATERIAL, "b"),
                   C.EntryChange(C.MOVED, "c")]
        self.assertEqual(C.describe(changes), "1 material, 2 moved (source lines only)")
        self.assertFalse(C.only_moved(changes))
        self.assertTrue(C.only_moved(changes[::2]))
        self.assertFalse(C.only_moved([]))


if __name__ == "__main__":
    unittest.main()
