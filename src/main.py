"""Точка входа эмулятора командной оболочки."""

import sys

from config import parse_args, print_config, vfs_name
from shell import Shell


def main(argv=None):
    """Запустить эмулятор и вернуть код завершения.

    :param argv: параметры командной строки (по умолчанию из ОС).
    """
    config = parse_args(argv)
    print_config(config)
    shell = Shell(vfs_name(config.vfs), echo_input=not sys.stdin.isatty())
    return shell.run(config.script)


if __name__ == "__main__":
    sys.exit(main())
