"""Встроенные команды эмулятора.

Каждая команда — функция ``(shell, args) -> int``, возвращающая код
завершения. Ошибки, прерывающие команду целиком, сообщаются
исключением :class:`CommandError`; ошибки отдельных операндов
выводятся сразу, и команда продолжает работу.
"""

import posixpath
from operator import itemgetter

from errors import (STATUS_ERROR, STATUS_OK, STATUS_TROUBLE, CommandError,
                    ExitRequest)
from vfs import (CURRENT_DIR, IS_A_DIRECTORY, NOT_A_DIRECTORY, PARENT_DIR,
                 SEPARATOR, VfsError, VfsNotFoundError, path_str)

EXIT_CODE_MODULO = 256
MAX_EXIT_ARGS = 1
MAX_CD_ARGS = 1
SINGLE_OPERAND = 1

OPTION_PREFIX = "-"
OPTIONS_END = "--"
HIDDEN_PREFIX = "."

LS_OPTIONS = "al"
SHOW_ALL = "a"
LONG_FORMAT = "l"
CAT_OPTIONS = "n"
NUMBER_LINES = "n"
RM_OPTIONS = "rRf"
RECURSIVE = frozenset("rR")
FORCE = "f"
TOUCH_OPTIONS = "c"
NO_CREATE = "c"

DIR_MODE = "drwxr-xr-x"
FILE_MODE = "-rw-r--r--"
DIR_SIZE = 4096
SIZE_WIDTH = 6
NUMBER_WIDTH = 6
TIME_FORMAT = "%Y-%m-%d %H:%M"
ENTRY_SEPARATOR = "  "
NEWLINE = "\n"


def check_option(arg, allowed):
    """Проверить группу коротких опций вида ``-abc``.

    :return: множество букв опций.
    :raises CommandError: при неизвестной опции.
    """
    if arg.startswith(OPTIONS_END):
        raise CommandError(f"unrecognized option '{arg}'")
    for letter in arg[1:]:
        if letter not in allowed:
            raise CommandError(f"invalid option -- '{letter}'")
    return set(arg[1:])


def split_options(args, allowed):
    """Отделить короткие опции от операндов.

    Опции можно объединять (``-la``) и указывать после операндов;
    ``--`` завершает список опций, ``-`` считается операндом.

    :param args: аргументы команды.
    :param allowed: строка с допустимыми буквами опций.
    :return: пара ``(множество опций, список операндов)``.
    :raises CommandError: при неизвестной опции.
    """
    flags, operands = set(), []
    for index, arg in enumerate(args):
        if arg == OPTIONS_END:
            operands.extend(args[index + 1:])
            break
        if arg.startswith(OPTION_PREFIX) and arg != OPTION_PREFIX:
            flags.update(check_option(arg, allowed))
        else:
            operands.append(arg)
    return flags, operands


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


def cmd_pwd(shell, args):
    """Вывести абсолютный путь текущего каталога: ``pwd``."""
    if args:
        raise CommandError("too many arguments")
    shell.write(path_str(shell.cwd))
    return STATUS_OK


def cmd_cd(shell, args):
    """Сменить текущий каталог: ``cd [DIR]``.

    Без аргумента выполняется переход в корень VFS, который служит
    домашним каталогом.
    """
    if len(args) > MAX_CD_ARGS:
        raise CommandError("too many arguments")
    target = args[0] if args else SEPARATOR
    try:
        node, names = shell.vfs.resolve(target, shell.cwd)
    except VfsError as exc:
        raise CommandError(f"{target}: {exc}") from None
    if not node.is_dir:
        raise CommandError(f"{target}: {NOT_A_DIRECTORY}")
    shell.cwd = names
    return STATUS_OK


def lookup_operands(shell, paths):
    """Найти операнды ``ls`` и разделить их на файлы и каталоги.

    Несуществующие пути сразу сообщаются как ошибки.

    :return: ``(файлы, каталоги, код)``; файлы и каталоги — списки
        пар ``(путь, узел)``, отсортированные по пути.
    """
    files, dirs = [], []
    status = STATUS_OK
    for path in paths:
        try:
            node, _ = shell.vfs.resolve(path, shell.cwd)
        except VfsError as exc:
            shell.error(f"ls: cannot access '{path}': {exc}")
            status = STATUS_TROUBLE
            continue
        (dirs if node.is_dir else files).append((path, node))
    by_path = itemgetter(0)
    return sorted(files, key=by_path), sorted(dirs, key=by_path), status


def dir_entries(shell, path, node, flags):
    """Список пар ``(имя, узел)`` с содержимым каталога для ``ls``.

    Скрытые файлы (имя начинается с точки) показываются только с
    опцией ``-a``, которая также добавляет записи ``.`` и ``..``.
    """
    show_all = SHOW_ALL in flags
    entries = [(name, child)
               for name, child in sorted(node.children.items())
               if show_all or not name.startswith(HIDDEN_PREFIX)]
    if not show_all:
        return entries
    parent, _ = shell.vfs.resolve(path + SEPARATOR + PARENT_DIR, shell.cwd)
    return [(CURRENT_DIR, node), (PARENT_DIR, parent)] + entries


def long_entry(name, node):
    """Строка подробного формата ``ls -l`` для одного узла."""
    mode = DIR_MODE if node.is_dir else FILE_MODE
    size = DIR_SIZE if node.is_dir else len(node.data)
    stamp = node.mtime.strftime(TIME_FORMAT)
    return f"{mode} {size:>{SIZE_WIDTH}} {stamp} {name}"


def print_entries(shell, entries, flags):
    """Вывести записи ``ls`` в кратком или подробном формате."""
    if LONG_FORMAT in flags:
        for name, node in entries:
            shell.write(long_entry(name, node))
    elif entries:
        shell.write(ENTRY_SEPARATOR.join(name for name, _ in entries))


def cmd_ls(shell, args):
    """Вывести содержимое каталогов: ``ls [-a] [-l] [PATH...]``.

    ``-a`` — показывать скрытые файлы, ``.`` и ``..``;
    ``-l`` — подробный формат: тип и права, размер, время, имя.
    Для файла выводится его имя. При нескольких операндах сначала
    выводятся файлы, затем каталоги с заголовками.
    """
    flags, paths = split_options(args, LS_OPTIONS)
    operands = paths or [CURRENT_DIR]
    files, dirs, status = lookup_operands(shell, operands)
    if files:
        print_entries(shell, files, flags)
    headers = len(operands) > SINGLE_OPERAND
    for index, (path, node) in enumerate(dirs):
        if files or index:
            shell.write()
        if headers:
            shell.write(f"{path}:")
        print_entries(shell, dir_entries(shell, path, node, flags), flags)
    return status


def read_file(shell, command, path):
    """Прочитать текст файла VFS.

    Двоичные данные возвращаются в base64. При ошибке выводится
    сообщение и возвращается ``None``.
    """
    try:
        node, _ = shell.vfs.resolve(path, shell.cwd)
    except VfsError as exc:
        shell.error(f"{command}: {path}: {exc}")
        return None
    if node.is_dir:
        shell.error(f"{command}: {path}: {IS_A_DIRECTORY}")
        return None
    return node.text()


def print_files(shell, command, paths, transform):
    """Вывести файлы, преобразовав текст каждого функцией ``transform``.

    Ошибка в одном файле не мешает выводу остальных.

    :return: код завершения (1, если хотя бы один файл не прочитан).
    """
    if not paths:
        raise CommandError("missing file operand")
    status = STATUS_OK
    for path in paths:
        text = read_file(shell, command, path)
        if text is None:
            status = STATUS_ERROR
        else:
            shell.write_text(transform(text))
    return status


class LineNumberer:
    """Нумерация строк, продолжающаяся от файла к файлу (``cat -n``)."""

    def __init__(self):
        """Начать нумерацию с первой строки."""
        self.last = 0

    def __call__(self, text):
        """Пронумеровать строки текста."""
        lines = text.splitlines()
        numbered = [f"{self.last + index:>{NUMBER_WIDTH}}\t{line}"
                    for index, line in enumerate(lines, start=1)]
        self.last += len(lines)
        return NEWLINE.join(numbered)


def keep_text(text):
    """Вернуть текст без изменений."""
    return text


def reverse_lines(text):
    """Расположить строки текста в обратном порядке."""
    return NEWLINE.join(reversed(text.splitlines()))


def cmd_cat(shell, args):
    """Вывести содержимое файлов: ``cat [-n] FILE...``.

    ``-n`` — нумеровать все строки вывода. Двоичные файлы выводятся
    в base64.
    """
    flags, paths = split_options(args, CAT_OPTIONS)
    transform = LineNumberer() if NUMBER_LINES in flags else keep_text
    return print_files(shell, "cat", paths, transform)


def cmd_tac(shell, args):
    """Вывести строки каждого файла в обратном порядке: ``tac FILE...``.

    Файлы обрабатываются по очереди, как в GNU tac.
    """
    _, paths = split_options(args, "")
    return print_files(shell, "tac", paths, reverse_lines)


def leave_removed_dir(shell, names):
    """Перейти в родительский каталог, если текущий был удалён.

    :param names: имена компонентов удалённого пути.
    """
    if shell.cwd[:len(names)] == names:
        shell.cwd = names[:-1]


def remove_path(shell, path, flags):
    """Удалить один операнд команды ``rm``.

    :raises CommandError: если путь удалить нельзя.
    """
    name = posixpath.basename(path.rstrip(SEPARATOR))
    if name in (CURRENT_DIR, PARENT_DIR):
        raise CommandError(
            f"refusing to remove '.' or '..' directory: skipping '{path}'")
    try:
        node, names = shell.vfs.resolve(path, shell.cwd)
    except VfsError as exc:
        if FORCE in flags and isinstance(exc, VfsNotFoundError):
            return
        raise CommandError(f"cannot remove '{path}': {exc}") from None
    if node.is_dir and not flags & RECURSIVE:
        raise CommandError(f"cannot remove '{path}': {IS_A_DIRECTORY}")
    if not names:
        raise CommandError("it is dangerous to operate recursively on '/'")
    shell.vfs.remove(names)
    leave_removed_dir(shell, names)


def cmd_rm(shell, args):
    """Удалить файлы и каталоги: ``rm [-r] [-f] PATH...``.

    ``-r`` (``-R``) — удалять каталоги вместе с содержимым;
    ``-f`` — не сообщать об отсутствующих путях (другие ошибки,
    например ``Not a directory``, сообщаются). Изменения
    выполняются только в памяти. Если удалён текущий каталог (или
    содержащий его), выполняется переход в родительский каталог
    удалённого.
    """
    flags, paths = split_options(args, RM_OPTIONS)
    if not paths and FORCE not in flags:
        raise CommandError("missing operand")
    status = STATUS_OK
    for path in paths:
        try:
            remove_path(shell, path, flags)
        except CommandError as exc:
            shell.error(f"rm: {exc}")
            status = STATUS_ERROR
    return status


def touch_path(shell, path, create):
    """Обновить время изменения узла или создать пустой файл.

    :param create: создавать ли отсутствующий файл.
    :raises VfsError: если файл создать нельзя.
    """
    try:
        node, _ = shell.vfs.resolve(path, shell.cwd)
    except VfsError:
        node = None
    if node is not None:
        node.touch()
    elif create:
        shell.vfs.create_file(path, shell.cwd)


def cmd_touch(shell, args):
    """Создать пустые файлы или обновить время: ``touch [-c] FILE...``.

    ``-c`` — не создавать отсутствующие файлы. Изменения выполняются
    только в памяти.
    """
    flags, paths = split_options(args, TOUCH_OPTIONS)
    if not paths:
        raise CommandError("missing file operand")
    status = STATUS_OK
    for path in paths:
        try:
            touch_path(shell, path, NO_CREATE not in flags)
        except VfsError as exc:
            shell.error(f"touch: cannot touch '{path}': {exc}")
            status = STATUS_ERROR
    return status


COMMANDS = {
    "cat": cmd_cat,
    "cd": cmd_cd,
    "exit": cmd_exit,
    "ls": cmd_ls,
    "pwd": cmd_pwd,
    "rm": cmd_rm,
    "tac": cmd_tac,
    "touch": cmd_touch,
    "vfs-init": cmd_vfs_init,
}
