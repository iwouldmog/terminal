"""Тесты сборки ZIP-архива VFS из каталога."""

import base64
import contextlib
import io
import os
import tempfile
import unittest

from mkvfs import build_archive, main
from vfs import VirtualFileSystem

BINARY = bytes(range(256))


class BuildArchiveTest(unittest.TestCase):
    """Проверки функции :func:`build_archive` и точки входа."""

    def setUp(self):
        """Создать каталог-источник с файлами разной вложенности."""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = os.path.join(self.tmp.name, "src")
        self.write("motd", b"hello\n")
        self.write("a/b/c.txt", b"deep\n")
        self.write("bin/tool.b64", base64.b64encode(BINARY))
        self.target = os.path.join(self.tmp.name, "out", "test.zip")

    def write(self, name, data):
        """Создать файл в каталоге-источнике."""
        path = os.path.join(self.source, *name.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as file:
            file.write(data)

    def test_build_and_load(self):
        """Собранный архив загружается в VFS со всей структурой."""
        build_archive(self.source, self.target)
        vfs = VirtualFileSystem.from_zip(self.target)
        self.assertEqual(vfs.count(), (3, 3))
        self.assertEqual(vfs.motd(), "hello\n")

    def test_b64_files_are_decoded(self):
        """Файлы ``.b64`` становятся двоичными без расширения."""
        build_archive(self.source, self.target)
        vfs = VirtualFileSystem.from_zip(self.target)
        tool = vfs.root.children["bin"].children["tool"]
        self.assertEqual(tool.data, BINARY)

    def test_main_success(self):
        """Точка входа возвращает 0 при успешной сборке."""
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main([self.source, self.target]), 0)
        self.assertTrue(os.path.isfile(self.target))

    def test_main_missing_source(self):
        """Отсутствующий каталог-источник — ошибка параметров."""
        missing = os.path.join(self.tmp.name, "none")
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                main([missing, self.target])
        self.assertEqual(ctx.exception.code, 2)

    def test_main_invalid_base64(self):
        """Повреждённый файл ``.b64`` — ошибка с кодом 1."""
        self.write("bad.b64", b"not base64!")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main([self.source, self.target]), 1)


if __name__ == "__main__":
    unittest.main()
