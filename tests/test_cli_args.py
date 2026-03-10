import unittest

from linuxConverter.cli import build_parser


class CliArgTests(unittest.TestCase):
    def test_translate_flag_defaults_false(self):
        parser = build_parser()
        args = parser.parse_args([])
        self.assertFalse(args.translate)
        self.assertFalse(args.disable_translate)

    def test_translate_flag_true_when_set(self):
        parser = build_parser()
        args = parser.parse_args(["--translate"])
        self.assertTrue(args.translate)
        self.assertFalse(args.disable_translate)

    def test_disable_translate_overrides(self):
        parser = build_parser()
        args = parser.parse_args(["--translate", "--disable-translate"])
        self.assertTrue(args.translate)
        self.assertTrue(args.disable_translate)


if __name__ == "__main__":
    unittest.main()
