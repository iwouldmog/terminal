"""Вспомогательные функции и базовый класс для тестов."""

import io
import os
import tempfile
import unittest
import zipfile
from functools import cached_property

from shell import Shell
from vfs import VirtualFileSystem


def make_zip(path, files, dirs=()):
    """Создать ZIP-архив с заданными файлами и каталогами.

    :param path: путь к создаваемому архиву.
    :param files: словарь «имя элемента → содержимое (bytes/str)».
    :param dirs: имена элементов-каталогов (с ``/`` на конце).
    """
    with zipfile.ZipFile(path, "w") as archive:
        for name in dirs:
            archive.writestr(name, b"")
        for name, data in files.items():
            archive.writestr(name, data)
    return path


def make_vfs(tmp_dir, files, dirs=(), name="test.zip"):
    """Создать архив во временном каталоге и загрузить из него VFS."""
    path = make_zip(os.path.join(tmp_dir, name), files, dirs)
    return VirtualFileSystem.from_zip(path)


def make_shell(vfs=None):
    """Создать оболочку с перехваченными потоками вывода."""
    return Shell(vfs, out=io.StringIO(), err=io.StringIO())


class TempDirTestCase(unittest.TestCase):
    """Базовый класс тестов с временным каталогом.

    Каталог создаётся при первом обращении к :attr:`tmp_dir` и
    удаляется после теста. ``unittest`` создаёт новый объект класса
    для каждого теста, поэтому у каждого теста свой каталог.
    """

    @cached_property
    def tmp_dir(self):
        """Путь к временному каталогу теста."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return tmp.name

    def tmp_path(self, name):
        """Путь к файлу ``name`` во временном каталоге."""
        return os.path.join(self.tmp_dir, name)
