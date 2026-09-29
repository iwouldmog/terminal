"""Встроенные команды эмулятора.

Каждая команда — функция ``(shell, args) -> int``, возвращающая код
завершения. Ошибки сообщаются исключением :class:`CommandError`.
"""

from errors import STATUS_OK, CommandError, ExitRequest

EXIT_CODE_MODULO = 256
MAX_EXIT_ARGS = 1


def print_stub(shell, name, args):
    """Вывести имя команды-заглушки и переданные ей аргументы.

    :param shell: оболочка, в которой выполняется команда.
    :param name: имя команды.
    :param args: список аргументов.
    :return: код успешного завершения.
    """
    shell.write(f"{name}: args={args}")
    return STATUS_OK


def cmd_ls(shell, args):
    """Заглушка ``ls``: вывести имя команды и аргументы."""
    return print_stub(shell, "ls", args)


def cmd_cd(shell, args):
    """Заглушка ``cd``: вывести имя команды и аргументы."""
    return print_stub(shell, "cd", args)


def cmd_exit(shell, args):
    """Завершить работу эмулятора: ``exit [N]``.

    Без аргумента используется код завершения последней команды,
    как в bash. Код берётся по модулю 256.

    :raises ExitRequest: запрос на завершение работы.
    :raises CommandError: при неверных аргументах.
    """
    if len(args) > MAX_EXIT_ARGS:
        raise CommandError("too many arguments")
    if not args:
        raise ExitRequest(shell.status)
    try:
        code = int(args[0])
    except ValueError:
        raise CommandError(
            f"{args[0]}: numeric argument required") from None
    raise ExitRequest(code % EXIT_CODE_MODULO)


COMMANDS = {
    "ls": cmd_ls,
    "cd": cmd_cd,
    "exit": cmd_exit,
}
