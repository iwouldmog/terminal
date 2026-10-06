"""Тесты оболочки: выполнение команд и цикл REPL."""

import unittest
from functools import cached_property
from unittest import mock

from helpers import TempDirTestCase, make_shell, make_vfs

from errors import ExitRequest
from shell import Shell
from vfs import VirtualFileSystem


class ExecuteTest(unittest.TestCase):
    """Выполнение отдельных команд."""

    @cached_property
    def shell(self):
        """Новая оболочка (создаётся при первом обращении в тесте)."""
        return make_shell()

    def test_prompt_contains_vfs_name(self):
        """Приглашение содержит имя VFS."""
        shell = Shell(VirtualFileSystem.empty("demo"))
        self.assertEqual(shell.prompt(), "demo:/$ ")

    def test_command_output(self):
        """Вывод команды попадает в поток стандартного вывода."""
        status = self.shell.execute("pwd")
        self.assertEqual(status, 0)
        self.assertEqual(self.shell.out.getvalue(), "/\n")

    def test_command_error(self):
        """Ошибка команды выводится в поток ошибок с её именем."""
        status = self.shell.execute("cd /none")
        self.assertEqual(status, 1)
        self.assertEqual(
            self.shell.err.getvalue(), "cd: /none: No such file or directory\n"
        )

    def test_empty_line_keeps_status(self):
        """Пустая строка не меняет код последней команды."""
        self.shell.execute("unknown")
        self.assertEqual(self.shell.execute("   "), 127)

    def test_unknown_command(self):
        """Неизвестная команда даёт ошибку и код 127."""
        status = self.shell.execute("foo bar")
        self.assertEqual(status, 127)
        self.assertEqual(self.shell.err.getvalue(), "foo: command not found\n")

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
            self.shell.err.getvalue(), "exit: abc: numeric argument required\n"
        )

    def test_exit_too_many_args(self):
        """Лишние аргументы exit — ошибка, работа продолжается."""
        status = self.shell.execute("exit 1 2")
        self.assertEqual(status, 1)
        self.assertIn("too many arguments", self.shell.err.getvalue())


class VfsCommandsTest(TempDirTestCase):
    """Работа оболочки с VFS: motd и команда vfs-init."""

    @cached_property
    def shell(self):
        """Оболочка с VFS из архива во временном каталоге."""
        files = {"motd": "Hello!\n", "a/b/c.txt": "c"}
        return make_shell(make_vfs(self.tmp_dir, files))

    def test_prompt_contains_vfs_name(self):
        """Приглашение содержит имя архива VFS."""
        self.assertEqual(self.shell.prompt(), "test:/$ ")

    def test_motd(self):
        """Сообщение motd выводится как есть."""
        self.shell.show_motd()
        self.assertEqual(self.shell.out.getvalue(), "Hello!\n")

    def test_no_motd(self):
        """Без файла motd ничего не выводится."""
        shell = make_shell()
        shell.show_motd()
        self.assertEqual(shell.out.getvalue(), "")

    def test_vfs_init(self):
        """vfs-init очищает VFS в памяти и физический архив."""
        self.shell.cwd = ["a"]
        self.assertEqual(self.shell.execute("vfs-init"), 0)
        self.assertEqual(self.shell.vfs.count(), (0, 0))
        self.assertEqual(self.shell.cwd, [])
        reloaded = VirtualFileSystem.from_zip(self.shell.vfs.source)
        self.assertEqual(reloaded.count(), (0, 0))

    def test_vfs_init_with_args(self):
        """vfs-init не принимает аргументов."""
        self.assertEqual(self.shell.execute("vfs-init now"), 1)
        self.assertEqual(
            self.shell.err.getvalue(), "vfs-init: too many arguments\n")
        self.assertEqual(self.shell.vfs.count(), (2, 2))

    def test_vfs_init_write_error(self):
        """Ошибка записи архива сообщается пользователю."""
        self.shell.vfs.source = self.tmp_dir
        self.assertEqual(self.shell.execute("vfs-init"), 1)
        self.assertIn("vfs-init: cannot write", self.shell.err.getvalue())


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
        shell, code = self.run_with_input(["pwd", "exit 5", "pwd"])
        self.assertEqual(code, 5)
        self.assertEqual(shell.out.getvalue(), "/\n")

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
        shell, code = self.run_with_input(["bad", "pwd", "exit 0"])
        self.assertEqual(code, 0)
        self.assertEqual(shell.out.getvalue(), "/\n")


class ScriptTest(TempDirTestCase):
    """Выполнение стартового скрипта."""

    def write_script(self, text):
        """Сохранить текст скрипта во временный файл."""
        path = self.tmp_path("script.txt")
        with open(path, "w", encoding="utf-8") as script:
            script.write(text)
        return path

    def run_script(self, text, lines=()):
        """Запустить оболочку со скриптом и строками ввода."""
        shell = make_shell(VirtualFileSystem.empty("demo"))
        inputs = list(lines) + [EOFError()]
        with mock.patch("builtins.input", side_effect=inputs):
            code = shell.run(self.write_script(text))
        return shell, code

    def test_input_and_output_are_shown(self):
        """Выводится приглашение с командой и результат команды."""
        shell, _ = self.run_script("ls -a\n\npwd\n")
        self.assertEqual(
            shell.out.getvalue(), "demo:/$ ls -a\n.  ..\ndemo:/$ pwd\n/\n\n"
        )

    def test_errors_are_skipped(self):
        """Строки с ошибками пропускаются, скрипт продолжается."""
        shell, _ = self.run_script("bad\nexit x\npwd\n")
        self.assertIn("demo:/$ pwd\n/\n", shell.out.getvalue())
        self.assertEqual(
            shell.err.getvalue(),
            "bad: command not found\nexit: x: numeric argument required\n",
        )

    def test_exit_in_script(self):
        """Команда exit в скрипте завершает эмулятор."""
        shell, code = self.run_script("exit 4\npwd\n")
        self.assertEqual(code, 4)
        self.assertNotIn("pwd", shell.out.getvalue())

    def test_repl_after_script(self):
        """После скрипта продолжается диалог с пользователем."""
        _, code = self.run_script("pwd\n", ["exit 9"])
        self.assertEqual(code, 9)

    def test_missing_script(self):
        """Отсутствующий скрипт — ошибка с кодом 1."""
        shell = make_shell()
        code = shell.run(self.tmp_path("missing.txt"))
        self.assertEqual(code, 1)
        self.assertIn("No such file or directory", shell.err.getvalue())

    def test_binary_script(self):
        """Скрипт не в кодировке UTF-8 — ошибка с кодом 1."""
        path = self.tmp_path("binary.txt")
        with open(path, "wb") as script:
            script.write(b"\xff\xfe")
        shell = make_shell()
        self.assertEqual(shell.run(path), 1)
        self.assertIn("not a UTF-8 text file", shell.err.getvalue())


if __name__ == "__main__":
    unittest.main()
