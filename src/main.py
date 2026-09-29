"""Точка входа эмулятора командной оболочки."""

import sys

from config import parse_args, print_config
from errors import STATUS_ERROR
from shell import Shell
from vfs import VfsError, VirtualFileSystem


def load_vfs(path):
    """Загрузить VFS из архива или создать VFS по умолчанию."""
    if path is None:
        return VirtualFileSystem.empty()
    return VirtualFileSystem.from_zip(path)


def print_vfs_info(vfs):
    """Отладочный вывод сведений о загруженной VFS."""
    dirs, files = vfs.count()
    print(f"[debug] vfs loaded: name={vfs.name}, directories={dirs}, "
          f"files={files}", flush=True)


def main(argv=None):
    """Запустить эмулятор и вернуть код завершения.

    :param argv: параметры командной строки (по умолчанию из ОС).
    """
    config = parse_args(argv)
    print_config(config)
    try:
        vfs = load_vfs(config.vfs)
    except VfsError as exc:
        print(f"emulator: {exc}", file=sys.stderr, flush=True)
        return STATUS_ERROR
    print_vfs_info(vfs)
    shell = Shell(vfs, echo_input=not sys.stdin.isatty())
    shell.show_motd()
    return shell.run(config.script)


if __name__ == "__main__":
    sys.exit(main())
