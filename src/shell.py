"""Интерпретатор эмулятора: цикл REPL и выполнение команд."""

import sys

from commands import COMMANDS
from errors import (STATUS_ERROR, STATUS_INTERRUPTED, STATUS_NOT_FOUND,
                    STATUS_OK, CommandError, ExitRequest)
from line_parser import parse_line

DEFAULT_VFS_NAME = "vfs"


class Shell:
    """Командная оболочка эмулятора."""

    def __init__(self, vfs_name=DEFAULT_VFS_NAME, out=None, err=None,
                 echo_input=False):
        """Создать оболочку.

        :param vfs_name: имя VFS, отображаемое в приглашении.
        :param out: поток стандартного вывода (по умолчанию stdout).
        :param err: поток вывода ошибок (по умолчанию stderr).
        :param echo_input: повторять введённую строку после
            приглашения (нужно, когда ввод идёт не с терминала).
        """
        self.vfs_name = vfs_name
        self.out = out if out is not None else sys.stdout
        self.err = err if err is not None else sys.stderr
        self.echo_input = echo_input
        self.status = STATUS_OK

    def prompt(self):
        """Сформировать приглашение к вводу, содержащее имя VFS."""
        return f"{self.vfs_name}$ "

    def write(self, text=""):
        """Вывести строку в поток стандартного вывода."""
        print(text, file=self.out, flush=True)

    def error(self, text):
        """Вывести сообщение об ошибке в поток ошибок."""
        print(text, file=self.err, flush=True)

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

    def run(self):
        """Запустить диалог с пользователем.

        :return: код завершения эмулятора.
        """
        try:
            self.repl()
        except ExitRequest as request:
            return request.code
        return self.status
