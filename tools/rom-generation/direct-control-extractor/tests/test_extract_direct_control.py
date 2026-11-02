"""Tests for the direct-control extractor."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SOURCE_DIRECTORY = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_DIRECTORY))

import extract_direct_control as extractor  # noqa: E402


SIMPLE_CASE = """## 3. Sequencing

### 3.2 Cases

#### 3.2.1 Example

Applicable context:

```text
MS = FETCH
TS = 4
```

Assignment:

```text
MS_NEXT = EXECUTE
```

Commit:

```text
MS <- EXECUTE at TP4
```

Constraints:

- One constraint.

Sources:

- [Control](../control.md)
"""


class HeadingTests(unittest.TestCase):
    def test_parses_numbered_headings(self) -> None:
        headings = extractor.parse_headings(SIMPLE_CASE.splitlines())
        self.assertEqual(
            [(item.level, item.number, item.title) for item in headings],
            [
                (2, "3", "Sequencing"),
                (3, "3.2", "Cases"),
                (4, "3.2.1", "Example"),
            ],
        )

    def test_ignores_unnumbered_heading(self) -> None:
        headings = extractor.parse_headings(["## Appendix", "### 1.1 Case"])
        self.assertEqual(len(headings), 2)
        self.assertIsNone(headings[0].number)
        self.assertEqual(headings[1].number, "1.1")

    def test_child_definition_has_numbered_parent(self) -> None:
        definitions, diagnostics = extractor.extract_document(
            SIMPLE_CASE, "docs/01-example.md"
        )
        self.assertEqual(diagnostics, [])
        self.assertEqual(definitions[0]["group"], "3.2 Cases")

    def test_parent_with_child_is_not_extracted(self) -> None:
        definitions, _ = extractor.extract_document(
            SIMPLE_CASE, "docs/01-example.md"
        )
        self.assertEqual([item["id"] for item in definitions], ["01:3.2.1"])

    def test_level_two_boundary_prevents_source_leakage(self) -> None:
        text = SIMPLE_CASE + "\n## 4. Related Documents\n- [Other](../other.md)\n"
        definitions, _ = extractor.extract_document(text, "docs/01-example.md")
        self.assertEqual(
            definitions[0]["sources"],
            [{"label": "Control", "target": "../control.md"}],
        )


class SectionTests(unittest.TestCase):
    def test_extracts_direct_assignment_and_commit(self) -> None:
        definitions, diagnostics = extractor.extract_document(
            SIMPLE_CASE, "docs/01-example.md"
        )
        self.assertEqual(diagnostics, [])
        item = definitions[0]
        self.assertEqual(item["direct_assignments"], ["MS_NEXT = EXECUTE"])
        self.assertEqual(item["state_commits"], ["MS <- EXECUTE at TP4"])

    def test_extracts_micro_operation_assignments_separately(self) -> None:
        text = """### 4.2 Read

Applicable context:

```text
MEM_READ_TO_MB is selected
```

Micro-operation assignments:

```text
/RD = 0
/WR = 1
```

CPU output-drive states:

```text
CPU MDB driver = HIGH_Z
```
"""
        definitions, diagnostics = extractor.extract_document(
            text, "docs/02-example.md"
        )
        self.assertEqual(diagnostics, [])
        item = definitions[0]
        self.assertEqual(item["direct_assignments"], [])
        self.assertEqual(
            item["micro_operation_assignments"], ["/RD = 0\n/WR = 1"]
        )
        self.assertEqual(item["drive_states"], ["CPU MDB driver = HIGH_Z"])

    def test_extracts_control_supplied_value(self) -> None:
        text = """### 5.1 Value

Micro-operation assignments:

```text
DF_LOAD = 1
DF_SRC = Control
```

Control-supplied value:

```text
DF_VAL = IR_DF
```
"""
        definitions, diagnostics = extractor.extract_document(
            text, "docs/01-example.md"
        )
        self.assertEqual(diagnostics, [])
        self.assertEqual(
            definitions[0]["control_supplied_values"], ["DF_VAL = IR_DF"]
        )

    def test_extracts_fixed_control_supplied_value(self) -> None:
        text = """### 5.3 Clear

Control-supplied value:

```text
DIF_VAL = 0
```
"""
        definitions, diagnostics = extractor.extract_document(
            text, "docs/01-example.md"
        )
        self.assertEqual(diagnostics, [])
        self.assertEqual(
            definitions[0]["control_supplied_values"], ["DIF_VAL = 0"]
        )

    def test_extracts_drive_state_and_external_ownership(self) -> None:
        text = """### 5.4 DMA Read

CPU output-drive states:

```text
CPU MDB driver = HIGH_Z
```

External ownership:

```text
memory drives MDB
```
"""
        definitions, diagnostics = extractor.extract_document(
            text, "docs/02-example.md"
        )
        self.assertEqual(diagnostics, [])
        item = definitions[0]
        self.assertEqual(item["drive_states"], ["CPU MDB driver = HIGH_Z"])
        self.assertEqual(item["external_ownership"], ["memory drives MDB"])

    def test_extracts_constraints_and_sources(self) -> None:
        definitions, _ = extractor.extract_document(
            SIMPLE_CASE, "docs/01-example.md"
        )
        item = definitions[0]
        self.assertEqual(item["constraints"], ["One constraint."])
        self.assertEqual(
            item["sources"],
            [{"label": "Control", "target": "../control.md"}],
        )

    def test_preserves_prose_context_when_no_code_block_exists(self) -> None:
        text = """### 3.3.2 Running

Applicable context:

RUN = 1
AND
none of the halt conditions applies

Assignment:

```text
RUN_NEXT = 1
```
"""
        definitions, diagnostics = extractor.extract_document(
            text, "docs/01-example.md"
        )
        self.assertEqual(diagnostics, [])
        self.assertEqual(
            definitions[0]["applicable_context"],
            ["RUN = 1\nAND\nnone of the halt conditions applies"],
        )

    def test_preserves_multiline_boolean_context_code_block(self) -> None:
        text = """### 3.3.2 Continued Running

Applicable context:

```text
RUN = 1
NOT (
    HLT_REQ = 1
    AND MS = EXECUTE
    AND TS = 4
)
NOT (
    FP_SINGLE_STEP = 1
    AND TS = 4
)
```

Assignment:

```text
RUN_NEXT = 1
```
"""
        definitions, diagnostics = extractor.extract_document(
            text, "docs/01-example.md"
        )
        self.assertEqual(diagnostics, [])
        self.assertEqual(
            definitions[0]["applicable_context"],
            [
                "RUN = 1\n"
                "NOT (\n"
                "    HLT_REQ = 1\n"
                "    AND MS = EXECUTE\n"
                "    AND TS = 4\n"
                ")\n"
                "NOT (\n"
                "    FP_SINGLE_STEP = 1\n"
                "    AND TS = 4\n"
                ")"
            ],
        )

    def test_unstructured_assignment_is_error(self) -> None:
        text = """### 3.2.1 Case

Assignment:

MS_NEXT = FETCH
"""
        _, diagnostics = extractor.extract_document(text, "docs/01-example.md")
        self.assertEqual(diagnostics[0].code, "UNSTRUCTURED_FIELD")
        self.assertEqual(diagnostics[0].severity, "ERROR")

    def test_descriptive_section_is_not_definition(self) -> None:
        definitions, diagnostics = extractor.extract_document(
            "## 1. Purpose\n\nText only.\n", "docs/01-example.md"
        )
        self.assertEqual(definitions, [])
        self.assertEqual(diagnostics, [])

    def test_source_link_target_is_trimmed(self) -> None:
        text = """### 6.1 Bus

CPU output-drive state:

```text
CPU DB driver = HIGH_Z
```

Sources:

- [Matrix]( ../matrix.md)
"""
        definitions, _ = extractor.extract_document(text, "docs/02-example.md")
        self.assertEqual(definitions[0]["sources"][0]["target"], "../matrix.md")


class BuildTests(unittest.TestCase):
    def test_default_output_is_extracted_artifact(self) -> None:
        self.assertEqual(
            extractor.DEFAULT_JSON_OUTPUT.name,
            "direct-control-definitions.json",
        )

    def test_missing_source_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(extractor.ExtractionFailure):
                extractor.build_result(root, (root / "missing.md",))

    def test_duplicate_ids_are_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "docs" / "01-first.md"
            second = root / "other" / "01-second.md"
            first.parent.mkdir(parents=True)
            second.parent.mkdir(parents=True)
            first.write_text(SIMPLE_CASE, encoding="utf-8")
            second.write_text(SIMPLE_CASE, encoding="utf-8")
            _, diagnostics = extractor.build_result(root, (first, second))
            self.assertIn("DUPLICATE_DEFINITION_ID", [item.code for item in diagnostics])

    def test_result_is_json_serializable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "docs" / "01-example.md"
            source.parent.mkdir(parents=True)
            source.write_text(SIMPLE_CASE, encoding="utf-8")
            result, _ = extractor.build_result(root, (source,))
            json.dumps(result)


class RepositoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[4]
        paths = tuple(cls.root / path for path in extractor.SOURCE_PATHS)
        cls.result, cls.diagnostics = extractor.build_result(cls.root, paths)
        cls.by_id = {item["id"]: item for item in cls.result["definitions"]}

    def test_repository_extracts_without_diagnostics(self) -> None:
        self.assertEqual(self.diagnostics, [])

    def test_repository_definition_count(self) -> None:
        self.assertEqual(len(self.result["definitions"]), 55)

    def test_repository_ids_are_unique(self) -> None:
        ids = [item["id"] for item in self.result["definitions"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_hlt_capture_is_capture_only(self) -> None:
        item = self.by_id["01:3.4.4"]
        self.assertEqual(item["direct_assignments"], ["HLT_REQ_NEXT = 1"])
        self.assertEqual(item["state_commits"], ["HLT_REQ <- 1 at TP3"])

    def test_stop_capture_is_capture_only(self) -> None:
        item = self.by_id["01:3.4.3"]
        self.assertEqual(item["direct_assignments"], ["HLT_REQ_NEXT = 1"])
        self.assertEqual(item["state_commits"], ["HLT_REQ <- 1 at TP"])

    def test_field_values_are_separated_from_micro_operations(self) -> None:
        item = self.by_id["01:5.1"]
        self.assertEqual(item["control_supplied_values"], ["DF_VAL = IR_DF"])
        self.assertEqual(
            item["micro_operation_assignments"],
            ["DF_LOAD = 1\nDF_SRC  = Control"],
        )

    def test_fixed_dif_value_is_control_supplied(self) -> None:
        self.assertEqual(
            self.by_id["01:5.3"]["control_supplied_values"],
            ["DIF_VAL = 0"],
        )

    def test_iot_transfer_cases_are_independent(self) -> None:
        expected = {
            "01:5.5.1": "IOT_TRANSFER_LOAD = 1\nIOT_TRANSFER_VAL  = READ",
            "01:5.5.2": "IOT_TRANSFER_LOAD = 1\nIOT_TRANSFER_VAL  = WRITE",
            "01:5.5.3": "IOT_TRANSFER_LOAD = 1\nIOT_TRANSFER_VAL  = NONE",
            "01:5.5.4": "IOT_TRANSFER_LOAD = 1\nIOT_TRANSFER_VAL  = READ",
            "01:5.5.5": "IOT_TRANSFER_LOAD = 1\nIOT_TRANSFER_VAL  = WRITE",
        }
        for definition_id, assignment in expected.items():
            self.assertEqual(
                self.by_id[definition_id]["direct_assignments"], [assignment]
            )

    def test_memory_read_strobes_are_micro_operation_owned(self) -> None:
        item = self.by_id["02:4.2"]
        self.assertEqual(item["direct_assignments"], [])
        self.assertEqual(
            item["micro_operation_assignments"], ["/RD = 0\n/WR = 1"]
        )
        self.assertIn("CPU MDB driver = HIGH_Z", item["drive_states"][0])

    def test_memory_writes_preserve_distinct_data_sources(self) -> None:
        self.assertIn(
            "MDB_SRC = MB",
            self.by_id["02:4.3"]["micro_operation_assignments"][0],
        )
        self.assertIn(
            "MDB_SRC = FP_SR",
            self.by_id["02:4.4"]["micro_operation_assignments"][0],
        )

    def test_db_strobes_are_micro_operation_owned(self) -> None:
        for definition_id in ("02:6.2", "02:6.3"):
            item = self.by_id[definition_id]
            self.assertEqual(item["direct_assignments"], [])
            self.assertTrue(item["micro_operation_assignments"])
            self.assertTrue(item["drive_states"])

    def test_dma_ownership_releases_cpu_drivers(self) -> None:
        item = self.by_id["02:5.2"]
        self.assertEqual(item["direct_assignments"], ["/DMA_GRANT = 0"])
        self.assertIn("CPU AB driver  = HIGH_Z", item["drive_states"][0])
        self.assertIn("CPU MFB driver = HIGH_Z", item["drive_states"][0])

    def test_derived_iot_values_are_not_direct_assignments(self) -> None:
        item = self.by_id["02:7.2"]
        self.assertEqual(item["direct_assignments"], ["IOT_ACTIVE = 1"])
        self.assertEqual(item["derived_values"], ["IOA = IR_IOA\nIOP = IR[2:0]"])

    def test_initialization_cases_are_distinct(self) -> None:
        self.assertEqual(
            self.by_id["02:8.2"]["direct_assignments"], ["/INITIALIZE = 0"]
        )
        self.assertEqual(
            self.by_id["02:8.3"]["direct_assignments"], ["/INITIALIZE = 0"]
        )
        self.assertEqual(
            self.by_id["02:8.4"]["direct_assignments"], ["/INITIALIZE = 1"]
        )

    def test_structured_fields_do_not_contain_markdown_fences(self) -> None:
        for item in self.result["definitions"]:
            for field in extractor.CODE_FIELDS:
                self.assertFalse(
                    any("```" in value for value in item[field]),
                    (item["id"], field),
                )


if __name__ == "__main__":
    unittest.main()
