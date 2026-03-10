import unittest

from linuxConverter.pipeline_parser import parse_pipeline
from linuxConverter.translator import Translator


class TranslatorTests(unittest.TestCase):
    def test_single_command_cmd(self):
        pipeline = parse_pipeline("ls")
        result = Translator("cmd").translate(pipeline)
        self.assertEqual(result.translated, "dir")
        self.assertEqual(result.warnings, [])

    def test_powershell_pipeline_golden(self):
        pipeline = parse_pipeline("ls | grep log")
        result = Translator("powershell").translate(pipeline)
        self.assertEqual(result.translated, 'Get-ChildItem | Select-String "log"')
        self.assertEqual(result.warnings, [])

    def test_cmd_pipeline_head_warning_golden(self):
        pipeline = parse_pipeline("ls | head -n 5")
        result = Translator("cmd").translate(pipeline)
        self.assertEqual(result.translated, "dir")
        self.assertIn("CMD does not support 'head'", result.warnings[0])

    def test_cmd_pipeline_with_grep(self):
        pipeline = parse_pipeline("ls | grep log")
        result = Translator("cmd").translate(pipeline)
        self.assertEqual(result.translated, 'dir | findstr "log"')
        self.assertEqual(result.warnings, [])

    def test_pipeline_only_command_outside_pipeline_warns(self):
        pipeline = parse_pipeline("grep error")
        result = Translator("powershell").translate(pipeline)
        self.assertEqual(result.translated, 'Select-String "error"')
        self.assertIn("'grep' is most useful inside pipelines", result.warnings)

    def test_unknown_command_marked_unsupported(self):
        pipeline = parse_pipeline("unknowncmd")
        result = Translator("cmd").translate(pipeline)
        self.assertEqual(result.translated, "unknowncmd")
        self.assertIn("unknowncmd", result.warnings[0])
        self.assertIn("unknowncmd", result.unsupported)

    def test_tail_pipeline_powershell(self):
        pipeline = parse_pipeline("ls | tail -n 3")
        result = Translator("powershell").translate(pipeline)
        self.assertEqual(result.translated, "Get-ChildItem | Select-Object -Last 3")
        self.assertEqual(result.warnings, [])

    def test_git_passthrough_cmd(self):
        pipeline = parse_pipeline('git commit -m "msg"')
        result = Translator("cmd").translate(pipeline)
        self.assertEqual(result.translated, 'git commit -m msg')
        self.assertEqual(result.warnings, [])

    def test_git_passthrough_powershell(self):
        pipeline = parse_pipeline("git status")
        result = Translator("powershell").translate(pipeline)
        self.assertEqual(result.translated, "git status")
        self.assertEqual(result.warnings, [])


if __name__ == "__main__":
    unittest.main()
