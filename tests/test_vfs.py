"""Тесты загрузки VFS из ZIP-архива и её очистки."""

import os
import tempfile
import unittest
import zipfile

from helpers import make_vfs, make_zip
from vfs import (DEFAULT_NAME, VfsError, VirtualFileSystem, decode_content,
                 path_str, vfs_name)

PNG_HEADER = b"\x89PNG\r\n\x1a\n"


class TempDirTest(unittest.TestCase):
    """Базовый класс тестов с временным каталогом."""

    def setUp(self):
        """Создать временный каталог."""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def path(self, name):
        """Путь к файлу во временном каталоге."""
        return os.path.join(self.tmp.name, name)


class LoadTest(TempDirTest):
    """Загрузка VFS из ZIP-архива."""

    def test_empty_default_vfs(self):
        """VFS по умолчанию пуста и не связана с архивом."""
        vfs = VirtualFileSystem.empty()
        self.assertEqual(vfs.name, DEFAULT_NAME)
        self.assertEqual(vfs.count(), (0, 0))
        self.assertIsNone(vfs.source)

    def test_name_and_source(self):
        """Имя VFS берётся из имени архива."""
        vfs = make_vfs(self.tmp.name, {"a.txt": "a"}, name="demo.zip")
        self.assertEqual(vfs.name, "demo")
        self.assertEqual(vfs.source, self.path("demo.zip"))

    def test_nested_tree(self):
        """Каталоги создаются и явно, и неявно (по путям файлов)."""
        files = {"a/b/c/d.txt": "deep", "top.txt": "top"}
        vfs = make_vfs(self.tmp.name, files, dirs=["a/", "empty/"])
        self.assertEqual(vfs.count(), (4, 2))
        node = vfs.root.children["a"].children["b"].children["c"]
        self.assertEqual(node.children["d.txt"].data, b"deep")
        self.assertTrue(vfs.root.children["empty"].is_dir)

    def test_binary_data(self):
        """Двоичные данные хранятся без изменений."""
        vfs = make_vfs(self.tmp.name, {"img.png": PNG_HEADER})
        self.assertEqual(vfs.root.children["img.png"].data, PNG_HEADER)

    def test_archive_is_not_modified(self):
        """Загрузка не изменяет архив и не распаковывает его."""
        path = make_zip(self.path("x.zip"), {"a/b.txt": "b"})
        with open(path, "rb") as archive:
            before = archive.read()
        VirtualFileSystem.from_zip(path)
        with open(path, "rb") as archive:
            self.assertEqual(archive.read(), before)
        self.assertEqual(os.listdir(self.tmp.name), ["x.zip"])

    def test_motd(self):
        """Файл motd читается из корня VFS."""
        vfs = make_vfs(self.tmp.name, {"motd": "hi\n", "d/motd": "no"})
        self.assertEqual(vfs.motd(), "hi\n")

    def test_no_motd(self):
        """Без файла motd (или если это каталог) сообщения нет."""
        vfs = make_vfs(self.tmp.name, {"motd/file": "x"})
        self.assertIsNone(vfs.motd())
        self.assertIsNone(VirtualFileSystem.empty().motd())


class LoadErrorTest(TempDirTest):
    """Ошибки загрузки VFS."""

    def assert_load_error(self, path, reason):
        """Проверить, что загрузка завершается ошибкой ``reason``."""
        with self.assertRaises(VfsError) as ctx:
            VirtualFileSystem.from_zip(path)
        self.assertIn(reason, str(ctx.exception))

    def test_missing_file(self):
        """Архив не существует."""
        self.assert_load_error(
            self.path("none.zip"), "No such file or directory")

    def test_directory(self):
        """Вместо архива указан каталог."""
        self.assert_load_error(self.tmp.name, "Is a directory")

    def test_not_zip(self):
        """Файл не является ZIP-архивом."""
        path = self.path("text.zip")
        with open(path, "w", encoding="utf-8") as text:
            text.write("plain text")
        self.assert_load_error(path, "File is not a zip file")

    def test_file_and_dir_conflict(self):
        """Одно имя не может быть и файлом, и каталогом."""
        path = make_zip(self.path("c.zip"), {"a": "file", "a/b": "x"})
        self.assert_load_error(path, "is both a file and a directory")

    def test_unsafe_path(self):
        """Пути с ``..`` запрещены."""
        path = make_zip(self.path("u.zip"), {"../evil.txt": "x"})
        self.assert_load_error(path, "unsafe path")


class ResetTest(TempDirTest):
    """Замена VFS на VFS по умолчанию."""

    def test_reset_clears_memory_and_archive(self):
        """Очищаются дерево в памяти и физический архив."""
        vfs = make_vfs(self.tmp.name, {"motd": "hi", "a/b.txt": "b"})
        vfs.reset()
        self.assertEqual(vfs.count(), (0, 0))
        with zipfile.ZipFile(vfs.source) as archive:
            self.assertEqual(archive.namelist(), [])

    def test_reset_without_source(self):
        """VFS без архива очищается только в памяти."""
        vfs = VirtualFileSystem.empty()
        vfs.reset()
        self.assertEqual(vfs.count(), (0, 0))

    def test_reset_write_error(self):
        """Ошибка записи архива не очищает VFS."""
        vfs = make_vfs(self.tmp.name, {"a.txt": "a"})
        vfs.source = self.tmp.name
        with self.assertRaises(VfsError):
            vfs.reset()
        self.assertEqual(vfs.count(), (0, 1))


class HelpersTest(unittest.TestCase):
    """Вспомогательные функции модуля vfs."""

    def test_decode_text(self):
        """Текст в UTF-8 возвращается как есть."""
        self.assertEqual(decode_content("привет".encode()), "привет")

    def test_decode_binary(self):
        """Двоичные данные кодируются в base64."""
        self.assertEqual(decode_content(PNG_HEADER), "iVBORw0KGgo=\n")

    def test_vfs_name(self):
        """Имя VFS — имя файла без расширения."""
        self.assertEqual(vfs_name("data/demo.zip"), "demo")
        self.assertEqual(vfs_name("/tmp/archive"), "archive")
        self.assertEqual(vfs_name("dir/deep/"), "deep")

    def test_path_str(self):
        """Абсолютный путь собирается из компонентов."""
        self.assertEqual(path_str([]), "/")
        self.assertEqual(path_str(["home", "user"]), "/home/user")


if __name__ == "__main__":
    unittest.main()
