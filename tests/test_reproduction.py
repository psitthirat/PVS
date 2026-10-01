"""Public checks using synthetic inputs only; no respondent data are loaded."""
import os
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from docx import Document

from pvs import analysis, preparation as prep, tables as run_all, sampling


class PackagePathTests(unittest.TestCase):
    def test_installed_cli_uses_explicit_workspace_from_another_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            workspace.mkdir()
            env = dict(os.environ)
            env.pop("PVS_THAI_REPORT", None)
            env["PVS_PROJECT_ROOT"] = str(Path(directory) / "wrong-workspace")
            result = subprocess.run(
                [sys.executable, "-m", "pvs", "tables", "--project-root", str(workspace)],
                cwd=directory, env=env, text=True, capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(str(workspace / "data/reference/thai_report.docx"), result.stderr)
            self.assertFalse((workspace / "output").exists())

    def test_mappings_and_outputs_follow_workspace_override(self):
        with tempfile.TemporaryDirectory() as directory:
            env = dict(os.environ, PVS_PROJECT_ROOT=directory)
            result = subprocess.run(
                [sys.executable, "-c",
                 "from pvs.paths import ROOT, MAPPINGS, OUTPUT; "
                 "assert MAPPINGS == ROOT / 'data/mappings'; "
                 "assert OUTPUT == ROOT / 'output'; print(ROOT)"],
                cwd=directory, env=env, text=True, capture_output=True, check=True,
            )
            self.assertEqual(result.stdout.strip(), str(Path(directory).resolve()))


class SamplingInputTests(unittest.TestCase):
    def test_explicit_path_and_environment_override(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sampling.docx"
            document = Document()
            table = document.add_table(rows=1, cols=6)
            for cell, value in zip(
                table.rows[0].cells,
                ["เขตที่ 1", "1,000", "600", "400", "60", "40"],
            ):
                cell.text = value
            document.save(path)
            with patch.dict(os.environ, {"PVS_THAI_REPORT": str(path)}):
                allocation = sampling.planned_allocation()
            self.assertEqual(allocation.iloc[0]["Planned total"], 100)
            self.assertEqual(allocation.iloc[0]["Population"], 1000)
            pd.testing.assert_frame_equal(allocation, sampling.planned_allocation(path))

    def test_missing_report_fails_before_loading_private_data(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"PVS_THAI_REPORT": str(Path(directory) / "missing.docx")}):
                with patch.object(run_all.prep, "load") as load:
                    with self.assertRaisesRegex(FileNotFoundError, "PVS_THAI_REPORT"):
                        run_all.main()
                    load.assert_not_called()


class DenominatorTests(unittest.TestCase):
    def test_binary_summary_excludes_missing_responses_from_denominator(self):
        group = prep.GROUPS[0]
        frame = pd.DataFrame({
            "outcome": ["yes", "no", None, "yes"],
            "provider_group": [group, group, group, None],
        })
        cells, _, _ = analysis.describe_binary(frame, "outcome", "yes")
        self.assertEqual(cells[group]["k"], 1)
        self.assertEqual(cells[group]["n"], 2)
        self.assertEqual(cells[group]["pct"], 50)
        self.assertEqual(cells[prep.GROUPS[1]]["fmt"], "--")

    def test_zero_denominator_is_missing_not_zero_percent(self):
        self.assertTrue(all(np.isnan(value) for value in analysis.prop_ci(0, 0)))

    def test_missing_p_values_do_not_change_multiplicity_family(self):
        adjusted = analysis.bh([0.01, np.nan, 0.04, 0.03])
        np.testing.assert_allclose(adjusted, [0.03, np.nan, 0.04, 0.04], equal_nan=True)


if __name__ == "__main__":
    unittest.main()
