"""Встроенные команды эмулятора.

Каждая команда — функция ``(shell, args) -> int``, возвращающая код
завершения. Ошибки сообщаются исключением :class:`CommandError`.
"""

from errors import STATUS_OK, CommandError, ExitRequest
from vfs import VfsError

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


def cmd_vfs_init(shell, args):
    """Заменить текущую VFS на VFS по умолчанию: ``vfs-init``.

    Содержимое VFS в памяти и её физическое представление (ZIP-архив)
    очищаются, текущим каталогом становится корень.
    """
    if args:
        raise CommandError("too many arguments")
    try:
        shell.vfs.reset()
    except VfsError as exc:
        raise CommandError(str(exc)) from None
    shell.cwd = []
    return STATUS_OK


COMMANDS = {
    "ls": cmd_ls,
    "cd": cmd_cd,
    "exit": cmd_exit,
    "vfs-init": cmd_vfs_init,
}
