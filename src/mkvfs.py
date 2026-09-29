"""Сборка ZIP-архива VFS из каталога файловой системы ОС.

Использование: ``python3 src/mkvfs.py SOURCE_DIR ARCHIVE``.

Файлы с расширением ``.b64`` декодируются из base64 и попадают в
архив как двоичные файлы без этого расширения. Так двоичные данные
хранятся в репозитории в текстовом виде.
"""

import argparse
import base64
import binascii
import os
import sys
import zipfile

from errors import STATUS_ERROR, STATUS_OK

B64_SUFFIX = ".b64"


def archive_name(source, path):
    """Имя элемента архива для пути внутри каталога ``source``."""
    return os.path.relpath(path, source).replace(os.sep, "/")


def read_data(path):
    """Прочитать файл; для ``.b64`` вернуть декодированные данные."""
    with open(path, "rb") as source:
        data = source.read()
    if path.endswith(B64_SUFFIX):
        return base64.b64decode(data)
    return data


def add_dir(archive, source, path):
    """Добавить в архив элемент-каталог."""
    info = zipfile.ZipInfo.from_file(
        path, archive_name(source, path), strict_timestamps=False)
    archive.writestr(info, b"")


def add_file(archive, source, path):
    """Добавить в архив файл (``.b64`` — в декодированном виде)."""
    name = archive_name(source, path)
    if name.endswith(B64_SUFFIX):
        name = name[:-len(B64_SUFFIX)]
    info = zipfile.ZipInfo.from_file(path, name, strict_timestamps=False)
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, read_data(path))


def build_archive(source, target):
    """Упаковать каталог ``source`` в ZIP-архив ``target``."""
    os.makedirs(os.path.dirname(target) or os.curdir, exist_ok=True)
    with zipfile.ZipFile(target, "w") as archive:
        for dirpath, dirnames, filenames in os.walk(source):
            dirnames.sort()
            if dirpath != source:
                add_dir(archive, source, dirpath)
            for name in sorted(filenames):
                add_file(archive, source, os.path.join(dirpath, name))


def main(argv=None):
    """Разобрать параметры, собрать архив и вернуть код завершения."""
    parser = argparse.ArgumentParser(
        prog="mkvfs", description="Сборка ZIP-архива VFS из каталога.")
    parser.add_argument("source", help="каталог с содержимым VFS")
    parser.add_argument("archive", help="путь к создаваемому архиву")
    args = parser.parse_args(argv)
    if not os.path.isdir(args.source):
        parser.error(f"'{args.source}' is not a directory")
    try:
        build_archive(args.source, args.archive)
    except (OSError, binascii.Error) as exc:
        print(f"mkvfs: {exc}", file=sys.stderr)
        return STATUS_ERROR
    print(f"mkvfs: {args.source} -> {args.archive}")
    return STATUS_OK


if __name__ == "__main__":
    sys.exit(main())
