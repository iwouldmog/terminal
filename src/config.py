"""Параметры командной строки эмулятора."""

import argparse
import sys

NOT_SET = "(not set)"


def build_parser():
    """Создать парсер параметров командной строки."""
    parser = argparse.ArgumentParser(
        prog="emulator",
        description="Эмулятор командной оболочки UNIX-подобной ОС.")
    parser.add_argument(
        "--vfs", metavar="PATH",
        help="путь к физическому расположению VFS")
    parser.add_argument(
        "--script", metavar="PATH",
        help="путь к стартовому скрипту")
    return parser


def parse_args(argv=None):
    """Разобрать параметры командной строки.

    :param argv: список параметров; по умолчанию ``sys.argv[1:]``.
    :return: пространство имён с полями ``vfs`` и ``script``.
    """
    return build_parser().parse_args(argv)


def print_config(config, out=None):
    """Отладочный вывод всех заданных параметров запуска.

    :param config: результат :func:`parse_args`.
    :param out: поток вывода (по умолчанию stdout).
    """
    out = out if out is not None else sys.stdout
    for name, value in vars(config).items():
        shown = NOT_SET if value is None else value
        print(f"[debug] {name}: {shown}", file=out, flush=True)
