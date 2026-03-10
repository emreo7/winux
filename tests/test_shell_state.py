import os
import tempfile
import unittest

from linuxConverter.shell_state import resolve_directory


class ShellStateTests(unittest.TestCase):
    def test_resolves_relative_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            subdir = os.path.join(tmp, "sub")
            os.makedirs(subdir)
            new_cwd, error = resolve_directory(tmp, ["sub"])
            self.assertIsNone(error)
            self.assertEqual(new_cwd, os.path.abspath(subdir))

    def test_invalid_directory_returns_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            new_cwd, error = resolve_directory(tmp, ["missing"])
            self.assertEqual(new_cwd, tmp)
            self.assertIsNotNone(error)

    def test_no_args_keeps_current_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            new_cwd, error = resolve_directory(tmp, [])
            self.assertIsNone(error)
            self.assertEqual(new_cwd, tmp)


if __name__ == "__main__":
    unittest.main()
