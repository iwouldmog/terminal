"""Тесты оболочки: выполнение команд и цикл REPL."""

import io
import os
import tempfile
import unittest
from unittest import mock

from errors import ExitRequest
from shell import Shell


def make_shell():
    """Создать оболочку с перехваченными потоками вывода."""
    return Shell(out=io.StringIO(), err=io.StringIO())


class ExecuteTest(unittest.TestCase):
    """Выполнение отдельных команд."""

    def setUp(self):
        """Подготовить новую оболочку для каждого теста."""
        self.shell = make_shell()

    def test_prompt_contains_vfs_name(self):
        """Приглашение содержит имя VFS."""
        shell = Shell(vfs_name="demo")
        self.assertIn("demo", shell.prompt())

    def test_ls_stub(self):
        """Заглушка ls выводит своё имя и аргументы."""
        status = self.shell.execute("ls -l /home")
        self.assertEqual(status, 0)
        self.assertEqual(
            self.shell.out.getvalue(), "ls: args=['-l', '/home']\n")

    def test_cd_stub(self):
        """Заглушка cd выводит своё имя и аргументы."""
        self.shell.execute("cd")
        self.assertEqual(self.shell.out.getvalue(), "cd: args=[]\n")

    def test_empty_line_keeps_status(self):
        """Пустая строка не меняет код последней команды."""
        self.shell.execute("unknown")
        self.assertEqual(self.shell.execute("   "), 127)

    def test_unknown_command(self):
        """Неизвестная команда даёт ошибку и код 127."""
        status = self.shell.execute("foo bar")
        self.assertEqual(status, 127)
        self.assertEqual(
            self.shell.err.getvalue(), "foo: command not found\n")

    def test_exit_without_args_uses_last_status(self):
        """exit без аргументов завершает с кодом последней команды."""
        self.shell.execute("unknown")
        with self.assertRaises(ExitRequest) as ctx:
            self.shell.execute("exit")
        self.assertEqual(ctx.exception.code, 127)

    def test_exit_with_code(self):
        """exit N завершает эмулятор с кодом N по модулю 256."""
        for line, code in (("exit 3", 3), ("exit 300", 44)):
            with self.assertRaises(ExitRequest) as ctx:
                self.shell.execute(line)
            self.assertEqual(ctx.exception.code, code)

    def test_exit_not_numeric(self):
        """Нечисловой аргумент exit — ошибка, работа продолжается."""
        status = self.shell.execute("exit abc")
        self.assertEqual(status, 1)
        self.assertEqual(
            self.shell.err.getvalue(),
            "exit: abc: numeric argument required\n")

    def test_exit_too_many_args(self):
        """Лишние аргументы exit — ошибка, работа продолжается."""
        status = self.shell.execute("exit 1 2")
        self.assertEqual(status, 1)
        self.assertIn("too many arguments", self.shell.err.getvalue())


class ReplTest(unittest.TestCase):
    """Диалог с пользователем в цикле REPL."""

    def run_with_input(self, lines):
        """Запустить REPL с заданными строками ввода."""
        shell = make_shell()
        with mock.patch("builtins.input", side_effect=lines):
            code = shell.run()
        return shell, code

    def test_exit_stops_repl(self):
        """Команда exit прекращает цикл и задаёт код завершения."""
        shell, code = self.run_with_input(["ls a", "exit 5", "cd b"])
        self.assertEqual(code, 5)
        self.assertEqual(shell.out.getvalue(), "ls: args=['a']\n")

    def test_end_of_input(self):
        """Конец ввода завершает REPL с кодом последней команды."""
        _, code = self.run_with_input(["foo", EOFError()])
        self.assertEqual(code, 127)

    def test_interrupt_continues(self):
        """Ctrl+C прерывает ввод строки, но не работу эмулятора."""
        _, code = self.run_with_input([KeyboardInterrupt(), "exit"])
        self.assertEqual(code, 130)

    def test_errors_do_not_stop_repl(self):
        """После ошибки диалог продолжается."""
        shell, code = self.run_with_input(["bad", "cd x", "exit 0"])
        self.assertEqual(code, 0)
        self.assertEqual(shell.out.getvalue(), "cd: args=['x']\n")


class ScriptTest(unittest.TestCase):
    """Выполнение стартового скрипта."""

    def setUp(self):
        """Создать временный каталог для скриптов."""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write_script(self, text):
        """Сохранить текст скрипта во временный файл."""
        path = os.path.join(self.tmp.name, "script.txt")
        with open(path, "w", encoding="utf-8") as script:
            script.write(text)
        return path

    def run_script(self, text, lines=()):
        """Запустить оболочку со скриптом и строками ввода."""
        shell = Shell("demo", out=io.StringIO(), err=io.StringIO())
        inputs = list(lines) + [EOFError()]
        with mock.patch("builtins.input", side_effect=inputs):
            code = shell.run(self.write_script(text))
        return shell, code

    def test_input_and_output_are_shown(self):
        """Выводится приглашение с командой и результат команды."""
        shell, _ = self.run_script("ls -a\n\ncd x\n")
        self.assertEqual(
            shell.out.getvalue(),
            "demo$ ls -a\nls: args=['-a']\n"
            "demo$ cd x\ncd: args=['x']\n\n")

    def test_errors_are_skipped(self):
        """Строки с ошибками пропускаются, скрипт продолжается."""
        shell, _ = self.run_script("bad\nexit x\nls\n")
        self.assertIn("ls: args=[]", shell.out.getvalue())
        self.assertEqual(
            shell.err.getvalue(),
            "bad: command not found\n"
            "exit: x: numeric argument required\n")

    def test_exit_in_script(self):
        """Команда exit в скрипте завершает эмулятор."""
        shell, code = self.run_script("exit 4\nls\n")
        self.assertEqual(code, 4)
        self.assertNotIn("ls:", shell.out.getvalue())

    def test_repl_after_script(self):
        """После скрипта продолжается диалог с пользователем."""
        _, code = self.run_script("ls\n", ["exit 9"])
        self.assertEqual(code, 9)

    def test_missing_script(self):
        """Отсутствующий скрипт — ошибка с кодом 1."""
        shell = make_shell()
        code = shell.run(os.path.join(self.tmp.name, "missing.txt"))
        self.assertEqual(code, 1)
        self.assertIn("No such file or directory", shell.err.getvalue())

    def test_binary_script(self):
        """Скрипт не в кодировке UTF-8 — ошибка с кодом 1."""
        path = os.path.join(self.tmp.name, "binary.txt")
        with open(path, "wb") as script:
            script.write(b"\xff\xfe")
        shell = make_shell()
        self.assertEqual(shell.run(path), 1)
        self.assertIn("not a UTF-8 text file", shell.err.getvalue())


if __name__ == "__main__":
    unittest.main()
