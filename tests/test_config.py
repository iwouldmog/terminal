"""Тесты разбора параметров командной строки."""

import contextlib
import io
import unittest

from config import DEFAULT_VFS_NAME, parse_args, print_config, vfs_name


class ParseArgsTest(unittest.TestCase):
    """Проверки функции :func:`parse_args`."""

    def test_no_params(self):
        """Без параметров оба значения не заданы."""
        config = parse_args([])
        self.assertIsNone(config.vfs)
        self.assertIsNone(config.script)

    def test_all_params(self):
        """Оба параметра задаются через пробел."""
        config = parse_args(["--vfs", "a.zip", "--script", "s.txt"])
        self.assertEqual(config.vfs, "a.zip")
        self.assertEqual(config.script, "s.txt")

    def test_equals_syntax(self):
        """Параметры задаются в форме ``--name=value``."""
        config = parse_args(["--script=s.txt", "--vfs=a.zip"])
        self.assertEqual((config.vfs, config.script), ("a.zip", "s.txt"))

    def test_invalid_params(self):
        """Ошибочные параметры завершают работу с кодом 2."""
        cases = (["--unknown"], ["--vfs"], ["--script"], ["extra"])
        for argv in cases:
            with self.subTest(argv=argv):
                with contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as ctx:
                        parse_args(argv)
                self.assertEqual(ctx.exception.code, 2)


class PrintConfigTest(unittest.TestCase):
    """Проверки отладочного вывода параметров."""

    def test_prints_all_params(self):
        """Выводятся все параметры, включая незаданные."""
        out = io.StringIO()
        print_config(parse_args(["--vfs", "a.zip"]), out)
        self.assertEqual(
            out.getvalue(),
            "[debug] vfs: a.zip\n[debug] script: (not set)\n")


class VfsNameTest(unittest.TestCase):
    """Проверки получения имени VFS из пути."""

    def test_default_name(self):
        """Без пути используется имя по умолчанию."""
        self.assertEqual(vfs_name(None), DEFAULT_VFS_NAME)

    def test_name_from_path(self):
        """Имя VFS — имя файла без расширения."""
        self.assertEqual(vfs_name("data/demo.zip"), "demo")
        self.assertEqual(vfs_name("/tmp/archive"), "archive")
        self.assertEqual(vfs_name("dir/deep/"), "deep")


if __name__ == "__main__":
    unittest.main()
