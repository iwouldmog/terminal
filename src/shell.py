"""Интерпретатор эмулятора: REPL и выполнение стартовых скриптов."""

import sys

from commands import COMMANDS
from errors import (STATUS_ERROR, STATUS_INTERRUPTED, STATUS_NOT_FOUND,
                    STATUS_OK, CommandError, ExitRequest)
from line_parser import parse_line
from vfs import VirtualFileSystem, path_str


def read_script(path):
    """Прочитать строки стартового скрипта из файла ОС.

    :param path: путь к скрипту.
    :return: список строк скрипта.
    :raises CommandError: если файл не удалось прочитать.
    """
    try:
        with open(path, encoding="utf-8") as script:
            return script.read().splitlines()
    except UnicodeDecodeError:
        raise CommandError("not a UTF-8 text file") from None
    except OSError as exc:
        raise CommandError(exc.strerror) from None


class Shell:
    """Командная оболочка эмулятора."""

    def __init__(self, vfs=None, out=None, err=None, echo_input=False):
        """Создать оболочку.

        :param vfs: виртуальная файловая система (по умолчанию —
            пустая VFS по умолчанию).
        :param out: поток стандартного вывода (по умолчанию stdout).
        :param err: поток вывода ошибок (по умолчанию stderr).
        :param echo_input: повторять введённую строку после
            приглашения (нужно, когда ввод идёт не с терминала).
        """
        self.vfs = vfs if vfs is not None else VirtualFileSystem.empty()
        self.cwd = []
        self.out = out if out is not None else sys.stdout
        self.err = err if err is not None else sys.stderr
        self.echo_input = echo_input
        self.status = STATUS_OK

    def prompt(self):
        """Сформировать приглашение: имя VFS и текущий каталог."""
        return f"{self.vfs.name}:{path_str(self.cwd)}$ "

    def write(self, text=""):
        """Вывести строку в поток стандартного вывода."""
        print(text, file=self.out, flush=True)

    def write_text(self, text):
        """Вывести многострочный текст, завершив его переводом строки."""
        if text:
            self.write(text[:-1] if text.endswith("\n") else text)

    def error(self, text):
        """Вывести сообщение об ошибке в поток ошибок."""
        print(text, file=self.err, flush=True)

    def show_motd(self):
        """Вывести сообщение из файла ``motd`` в корне VFS, если он есть."""
        text = self.vfs.motd()
        if text is not None:
            self.write_text(text)

    def execute(self, line):
        """Выполнить одну строку ввода.

        :param line: строка с командой и аргументами.
        :return: код завершения команды.
        :raises ExitRequest: если выполнена команда ``exit``.
        """
        name, args = parse_line(line)
        if name is None:
            return self.status
        command = COMMANDS.get(name)
        if command is None:
            self.error(f"{name}: command not found")
            self.status = STATUS_NOT_FOUND
            return self.status
        try:
            self.status = command(self, args)
        except CommandError as exc:
            self.error(f"{name}: {exc}")
            self.status = STATUS_ERROR
        return self.status

    def read_line(self):
        """Прочитать строку ввода; ``None`` означает конец ввода."""
        try:
            line = input(self.prompt())
        except EOFError:
            self.write()
            return None
        if self.echo_input:
            self.write(line)
        return line

    def repl(self):
        """Цикл чтения и выполнения команд до конца ввода."""
        while True:
            try:
                line = self.read_line()
            except KeyboardInterrupt:
                self.write()
                self.status = STATUS_INTERRUPTED
                continue
            if line is None:
                return
            self.execute(line)

    def run_script(self, path):
        """Выполнить стартовый скрипт, имитируя диалог с пользователем.

        Каждая непустая строка выводится после приглашения и
        выполняется. Строки с ошибками пропускаются.

        :param path: путь к скрипту в файловой системе ОС.
        :return: ``False``, если скрипт не удалось прочитать.
        """
        try:
            lines = read_script(path)
        except CommandError as exc:
            self.error(f"emulator: cannot read script '{path}': {exc}")
            return False
        for line in lines:
            if line.strip():
                self.write(self.prompt() + line)
                self.execute(line)
        return True

    def run(self, script=None):
        """Выполнить стартовый скрипт (если задан), затем диалог.

        :param script: путь к стартовому скрипту или ``None``.
        :return: код завершения эмулятора.
        """
        try:
            if script is not None and not self.run_script(script):
                return STATUS_ERROR
            self.repl()
        except ExitRequest as request:
            return request.code
        return self.status
