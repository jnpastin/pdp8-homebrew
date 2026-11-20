"""Tests for the control-design selection in design.py."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import design  # noqa: E402


class SelectionTests(unittest.TestCase):
    def test_default_is_v1_with_original_paths(self) -> None:  # V1-ONLY
        with mock.patch.dict(os.environ, clear=True):
            d = design.select()
        self.assertEqual(d.name, "v1")
        self.assertEqual(str(d.maintained), "rom/microcode/v1")
        self.assertEqual(str(d.build), "build/simulation_outputs/rom-generation")
        self.assertTrue(d.frozen)

    def test_environment_selects(self) -> None:
        with mock.patch.dict(os.environ, {design.ENVIRONMENT_VARIABLE: "v2"}):
            d = design.select()
        self.assertEqual(d.name, "v2")
        self.assertEqual(str(d.maintained), "rom/microcode/v2")
        self.assertFalse(d.frozen)

    def test_name_overrides_environment(self) -> None:
        with mock.patch.dict(os.environ, {design.ENVIRONMENT_VARIABLE: "v2"}):
            self.assertEqual(design.select("v1").name, "v1")

    def test_unknown_design_is_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            design.select("v9")

    def test_designs_do_not_share_paths(self) -> None:
        maintained = {d.maintained for d in design.DESIGNS.values()}
        build = {d.build for d in design.DESIGNS.values()}
        self.assertEqual(len(maintained), len(design.DESIGNS))
        self.assertEqual(len(build), len(design.DESIGNS))


if __name__ == "__main__":
    unittest.main()
