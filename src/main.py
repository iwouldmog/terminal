"""Точка входа эмулятора командной оболочки."""

import sys

from shell import Shell


def main():
    """Запустить эмулятор и вернуть код завершения."""
    shell = Shell(echo_input=not sys.stdin.isatty())
    return shell.run()


if __name__ == "__main__":
    sys.exit(main())
