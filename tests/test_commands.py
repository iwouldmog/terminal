"""Тесты команд ls, cd, pwd, cat, tac и разбора опций."""

import tempfile
import unittest

from commands import split_options
from errors import CommandError
from helpers import make_shell, make_vfs

FILES = {
    "motd": "Hello\n",
    "etc/hostname": "host\n",
    "home/user/.hidden": "secret\n",
    "home/user/docs/a.txt": "1\n2\n3\n",
    "home/user/docs/b.txt": "x\ny",
    "home/user/empty.txt": "",
    "bin/tool": b"\x00\xff\x10",
}


class CommandTestCase(unittest.TestCase):
    """Базовый класс: оболочка с тестовой VFS."""

    def setUp(self):
        """Создать оболочку с VFS из словаря ``FILES``."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.shell = make_shell(make_vfs(tmp.name, FILES))

    def run_cmd(self, line):
        """Выполнить строку и вернуть ``(код, stdout, stderr)``."""
        out, err = self.shell.out, self.shell.err
        out.seek(0)
        out.truncate()
        err.seek(0)
        err.truncate()
        status = self.shell.execute(line)
        return status, out.getvalue(), err.getvalue()


class SplitOptionsTest(unittest.TestCase):
    """Разбор коротких опций."""

    def test_combined_and_separate(self):
        """Опции объединяются и указываются после операндов."""
        flags, operands = split_options(["-la", "x", "-a"], "al")
        self.assertEqual(flags, {"l", "a"})
        self.assertEqual(operands, ["x"])

    def test_end_of_options(self):
        """После ``--`` всё считается операндами, ``-`` — операнд."""
        flags, operands = split_options(["-a", "--", "-l", "-"], "al")
        self.assertEqual((flags, operands), ({"a"}, ["-l", "-"]))

    def test_invalid_option(self):
        """Неизвестная короткая опция — ошибка."""
        with self.assertRaisesRegex(CommandError, "invalid option -- 'z'"):
            split_options(["-az"], "a")

    def test_long_option(self):
        """Длинные опции не поддерживаются."""
        with self.assertRaisesRegex(CommandError, "unrecognized option"):
            split_options(["--all"], "a")


class CdPwdTest(CommandTestCase):
    """Команды cd и pwd."""

    def test_pwd_root(self):
        """В начале работы текущий каталог — корень."""
        self.assertEqual(self.run_cmd("pwd"), (0, "/\n", ""))

    def test_cd_absolute_and_relative(self):
        """Переход по абсолютным и относительным путям."""
        self.run_cmd("cd /home/user")
        self.run_cmd("cd docs/../docs/.")
        self.assertEqual(self.run_cmd("pwd")[1], "/home/user/docs\n")
        self.assertEqual(self.shell.prompt(), "test:/home/user/docs$ ")

    def test_cd_parent_of_root(self):
        """``..`` в корне остаётся в корне."""
        self.run_cmd("cd ../..")
        self.assertEqual(self.shell.cwd, [])

    def test_cd_without_args(self):
        """cd без аргументов переходит в корень."""
        self.run_cmd("cd /etc")
        self.run_cmd("cd")
        self.assertEqual(self.shell.cwd, [])

    def test_cd_errors(self):
        """Ошибки cd не меняют текущий каталог."""
        self.run_cmd("cd /etc")
        cases = {
            "cd /none": "cd: /none: No such file or directory\n",
            "cd hostname": "cd: hostname: Not a directory\n",
            "cd hostname/..": "cd: hostname/..: Not a directory\n",
            "cd a b": "cd: too many arguments\n",
        }
        for line, message in cases.items():
            with self.subTest(line=line):
                self.assertEqual(self.run_cmd(line), (1, "", message))
        self.assertEqual(self.shell.cwd, ["etc"])

    def test_pwd_with_args(self):
        """pwd не принимает аргументов."""
        self.assertEqual(
            self.run_cmd("pwd x"), (1, "", "pwd: too many arguments\n"))


class LsTest(CommandTestCase):
    """Команда ls."""

    def test_current_dir(self):
        """Без аргументов выводится текущий каталог по алфавиту."""
        self.assertEqual(
            self.run_cmd("ls"), (0, "bin  etc  home  motd\n", ""))

    def test_hidden_files(self):
        """Скрытые файлы видны только с ``-a``."""
        self.run_cmd("cd /home/user")
        self.assertEqual(self.run_cmd("ls")[1], "docs  empty.txt\n")
        self.assertEqual(
            self.run_cmd("ls -a")[1], ".  ..  .hidden  docs  empty.txt\n")

    def test_long_format(self):
        """Подробный формат: тип, права, размер, время, имя."""
        lines = self.run_cmd("ls -l /home/user")[1].splitlines()
        self.assertEqual(len(lines), 2)
        self.assertRegex(lines[0], r"^drwxr-xr-x +4096 [\d-]+ [\d:]+ docs$")
        self.assertRegex(lines[1], r"^-rw-r--r-- +0 .* empty\.txt$")

    def test_file_operand(self):
        """Для файла выводится его имя в заданной форме."""
        self.assertEqual(self.run_cmd("ls etc/hostname")[1], "etc/hostname\n")

    def test_several_operands(self):
        """Файлы выводятся первыми, каталоги — с заголовками."""
        output = self.run_cmd("ls /home/user/docs motd /etc")[1]
        self.assertEqual(
            output, "motd\n\n/etc:\nhostname\n\n/home/user/docs:\n"
            "a.txt  b.txt\n")

    def test_empty_dir(self):
        """Пустой каталог ничего не выводит."""
        self.run_cmd("vfs-init")
        self.assertEqual(self.run_cmd("ls"), (0, "", ""))

    def test_errors(self):
        """Ошибки ls: несуществующий путь и неверная опция."""
        status, out, err = self.run_cmd("ls /none /etc")
        self.assertEqual((status, out), (2, "/etc:\nhostname\n"))
        self.assertEqual(
            err, "ls: cannot access '/none': No such file or directory\n")
        self.assertEqual(
            self.run_cmd("ls -q"), (1, "", "ls: invalid option -- 'q'\n"))


class CatTacTest(CommandTestCase):
    """Команды cat и tac."""

    def test_cat_files(self):
        """Файлы выводятся по порядку, перевод строки добавляется."""
        self.run_cmd("cd /home/user/docs")
        self.assertEqual(
            self.run_cmd("cat a.txt b.txt /motd"),
            (0, "1\n2\n3\nx\ny\nHello\n", ""))

    def test_cat_numbering(self):
        """``-n`` нумерует строки сквозным образом."""
        self.run_cmd("cd /home/user/docs")
        self.assertEqual(
            self.run_cmd("cat -n a.txt b.txt")[1],
            "     1\t1\n     2\t2\n     3\t3\n     4\tx\n     5\ty\n")

    def test_cat_empty_and_binary(self):
        """Пустой файл ничего не выводит, двоичный — выводится в base64."""
        self.assertEqual(self.run_cmd("cat home/user/empty.txt")[1], "")
        self.assertEqual(self.run_cmd("cat bin/tool")[1], "AP8Q\n")

    def test_cat_errors(self):
        """Ошибка в одном файле не мешает выводу остальных."""
        status, out, err = self.run_cmd("cat none /etc /motd")
        self.assertEqual((status, out), (1, "Hello\n"))
        self.assertEqual(
            err, "cat: none: No such file or directory\n"
            "cat: /etc: Is a directory\n")
        self.assertEqual(
            self.run_cmd("cat"), (1, "", "cat: missing file operand\n"))

    def test_tac(self):
        """tac выводит строки каждого файла в обратном порядке."""
        self.run_cmd("cd /home/user/docs")
        self.assertEqual(
            self.run_cmd("tac a.txt b.txt"), (0, "3\n2\n1\ny\nx\n", ""))

    def test_tac_errors(self):
        """Ошибки tac: нет операндов, каталог, неверная опция."""
        self.assertEqual(self.run_cmd("tac")[0], 1)
        status, out, err = self.run_cmd("tac /home /etc/hostname")
        self.assertEqual((status, out), (1, "host\n"))
        self.assertEqual(err, "tac: /home: Is a directory\n")
        self.assertEqual(self.run_cmd("tac -r motd")[0], 1)


if __name__ == "__main__":
    unittest.main()
