"""Виртуальная файловая система (VFS), хранящаяся в памяти.

Источником VFS служит ZIP-архив. Архив читается целиком в память и не
распаковывается на диск; изменения VFS выполняются только в памяти.
Исключение — служебная команда ``vfs-init``, которая очищает и
физическое представление VFS.
"""

import base64
import io
import os
import zipfile
import zlib
from datetime import datetime

SEPARATOR = "/"
CURRENT_DIR = "."
PARENT_DIR = ".."
DEFAULT_NAME = "vfs"
MOTD_NAME = "motd"
TEXT_ENCODING = "utf-8"
DOS_EPOCH = datetime(1980, 1, 1)
LOAD_ERRORS = (OSError, EOFError, RuntimeError, NotImplementedError,
               zipfile.BadZipFile, zlib.error)


class VfsError(Exception):
    """Ошибка работы с виртуальной файловой системой."""


class Node:
    """Узел VFS: каталог (словарь ``children``) или файл (``data``)."""

    def __init__(self, children=None, data=b"", mtime=None):
        """Создать узел.

        :param children: словарь «имя → узел» для каталога или
            ``None`` для файла.
        :param data: содержимое файла.
        :param mtime: время изменения (по умолчанию — текущее).
        """
        self.children = children
        self.data = data
        self.mtime = mtime if mtime is not None else datetime.now()

    @classmethod
    def directory(cls, mtime=None):
        """Создать пустой каталог."""
        return cls(children={}, mtime=mtime)

    @classmethod
    def file(cls, data=b"", mtime=None):
        """Создать файл с заданным содержимым."""
        return cls(data=data, mtime=mtime)

    @property
    def is_dir(self):
        """Является ли узел каталогом."""
        return self.children is not None

    def text(self):
        """Содержимое файла как текст; двоичные данные — в base64."""
        return decode_content(self.data)


def decode_content(data):
    """Преобразовать содержимое файла в текст для вывода.

    Текст в UTF-8 возвращается как есть, двоичные данные кодируются
    в base64 (по 76 символов в строке).
    """
    try:
        return data.decode(TEXT_ENCODING)
    except UnicodeDecodeError:
        return base64.encodebytes(data).decode("ascii")


def error_reason(exc):
    """Получить текст причины ошибки для сообщения пользователю."""
    if isinstance(exc, OSError) and exc.strerror:
        return exc.strerror
    return str(exc)


def vfs_name(path):
    """Получить имя VFS из пути к её физическому расположению.

    Именем служит имя файла без расширения: ``data/demo.zip`` даёт
    ``demo``.
    """
    base = os.path.basename(os.path.normpath(path))
    return os.path.splitext(base)[0] or DEFAULT_NAME


def path_str(names):
    """Собрать абсолютный путь из списка имён компонентов."""
    return SEPARATOR + SEPARATOR.join(names)


def entry_parts(filename):
    """Разбить имя элемента архива на компоненты пути.

    :raises VfsError: если путь выходит за пределы корня VFS.
    """
    parts = [part for part in filename.split(SEPARATOR)
             if part not in ("", CURRENT_DIR)]
    if PARENT_DIR in parts:
        raise VfsError(f"unsafe path in archive: '{filename}'")
    return parts


def entry_time(info):
    """Получить время изменения элемента архива."""
    try:
        return datetime(*info.date_time)
    except ValueError:
        return DOS_EPOCH


def conflict_error(name):
    """Создать ошибку совпадения имён файла и каталога в архиве."""
    return VfsError(
        f"invalid archive: '{name}' is both a file and a directory")


def make_dirs(root, parts, mtime):
    """Найти или создать цепочку каталогов и вернуть последний."""
    node = root
    for part in parts:
        child = node.children.get(part)
        if child is None:
            child = node.children[part] = Node.directory(mtime)
        elif not child.is_dir:
            raise conflict_error(part)
        node = child
    return node


def add_entry(root, info, data):
    """Добавить элемент ZIP-архива в дерево VFS."""
    parts = entry_parts(info.filename)
    if not parts:
        return
    mtime = entry_time(info)
    if info.is_dir():
        make_dirs(root, parts, mtime).mtime = mtime
        return
    parent = make_dirs(root, parts[:-1], mtime)
    name = parts[-1]
    existing = parent.children.get(name)
    if existing is not None and existing.is_dir:
        raise conflict_error(name)
    parent.children[name] = Node.file(data, mtime)


def load_tree(raw):
    """Построить дерево узлов по байтам ZIP-архива, не распаковывая."""
    root = Node.directory()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for info in archive.infolist():
            data = b"" if info.is_dir() else archive.read(info)
            add_entry(root, info, data)
    return root


class VirtualFileSystem:
    """Дерево каталогов и файлов VFS вместе с её источником."""

    def __init__(self, name, root, source=None):
        """Создать VFS.

        :param name: имя VFS для приглашения к вводу.
        :param root: корневой каталог (:class:`Node`).
        :param source: путь к ZIP-архиву или ``None``.
        """
        self.name = name
        self.root = root
        self.source = source

    @classmethod
    def empty(cls, name=DEFAULT_NAME):
        """Создать VFS по умолчанию — пустой корневой каталог."""
        return cls(name, Node.directory())

    @classmethod
    def from_zip(cls, path):
        """Загрузить VFS из ZIP-архива целиком в память.

        :raises VfsError: если архив не удалось прочитать.
        """
        try:
            with open(path, "rb") as source:
                root = load_tree(source.read())
        except LOAD_ERRORS + (VfsError,) as exc:
            raise VfsError(
                f"cannot load VFS '{path}': {error_reason(exc)}") from None
        return cls(vfs_name(path), root, path)

    def reset(self):
        """Заменить содержимое на VFS по умолчанию.

        Физическое представление (ZIP-архив) перезаписывается пустым
        архивом.

        :raises VfsError: если архив не удалось перезаписать.
        """
        if self.source is not None:
            try:
                zipfile.ZipFile(self.source, "w").close()
            except OSError as exc:
                raise VfsError(
                    f"cannot write '{self.source}': {error_reason(exc)}"
                ) from None
        self.root = Node.directory()

    def count(self):
        """Подсчитать каталоги (без корня) и файлы VFS."""
        dirs = files = 0
        stack = [self.root]
        while stack:
            for child in stack.pop().children.values():
                if child.is_dir:
                    dirs += 1
                    stack.append(child)
                else:
                    files += 1
        return dirs, files

    def motd(self):
        """Вернуть текст файла ``motd`` из корня VFS или ``None``."""
        node = self.root.children.get(MOTD_NAME)
        if node is None or node.is_dir:
            return None
        return node.text()
