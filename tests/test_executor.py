import subprocess
import unittest
from unittest.mock import patch

from linuxConverter.executor import execute_translation


class ExecuteTranslationTests(unittest.TestCase):
    def test_executes_powershell_with_expected_args(self):
        completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")
        with patch("subprocess.run", return_value=completed) as mock_run:
            result = execute_translation("powershell", "Get-Location", cwd="C:\\path")

        mock_run.assert_called_once_with(
            ["powershell", "-NoLogo", "-NoProfile", "-OutputFormat", "Text", "-Command", "Get-Location"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            cwd="C:\\path",
        )
        self.assertEqual(result.stdout, "ok")
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.returncode, 0)

    def test_executes_cmd_with_expected_args(self):
        completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")
        with patch("subprocess.run", return_value=completed) as mock_run:
            result = execute_translation("cmd", "dir", cwd="C:\\path")

        mock_run.assert_called_once_with(
            ["cmd", "/d", "/c", "dir"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            cwd="C:\\path",
        )
        self.assertEqual(result.stdout, "ok")
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.returncode, 0)

    def test_handles_missing_command_binary(self):
        with patch("subprocess.run", side_effect=FileNotFoundError("not found")):
            result = execute_translation("powershell", "Get-Location")

        self.assertEqual(result.returncode, 127)
        self.assertIn("not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
