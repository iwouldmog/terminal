"""Тесты команд rm и touch, изменяющих VFS только в памяти."""

import tempfile
import unittest

from helpers import make_shell, make_vfs
from vfs import DOS_EPOCH, VfsNotFoundError

FILES = {
    "motd": "Hello\n",
    "etc/hostname": "host\n",
    "home/user/docs/a.txt": "a\n",
    "home/user/docs/sub/b.txt": "b\n",
}


class ModifyTestCase(unittest.TestCase):
    """Базовый класс: оболочка с тестовой VFS."""

    def setUp(self):
        """Создать оболочку с VFS из словаря ``FILES``."""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.shell = make_shell(make_vfs(tmp.name, FILES))
        with open(self.shell.vfs.source, "rb") as archive:
            self.archive = archive.read()

    def run_cmd(self, line):
        """Выполнить строку и вернуть ``(код, stderr)``."""
        err = self.shell.err
        err.seek(0)
        err.truncate()
        status = self.shell.execute(line)
        return status, err.getvalue()

    def exists(self, path):
        """Существует ли путь в VFS."""
        try:
            self.shell.vfs.resolve(path, [])
        except VfsNotFoundError:
            return False
        return True

    def assert_archive_unchanged(self):
        """Проверить, что физический архив VFS не изменился."""
        with open(self.shell.vfs.source, "rb") as archive:
            self.assertEqual(archive.read(), self.archive)


class TouchTest(ModifyTestCase):
    """Команда touch."""

    def test_create_files(self):
        """Создаются пустые файлы по относительным и абсолютным путям."""
        self.run_cmd("cd /home/user")
        self.assertEqual(self.run_cmd("touch new.txt /top docs/sub/c"),
                         (0, ""))
        for path in ("/home/user/new.txt", "/top", "/home/user/docs/sub/c"):
            node, _ = self.shell.vfs.resolve(path, [])
            self.assertEqual(node.data, b"")
        self.assert_archive_unchanged()

    def test_update_mtime(self):
        """Для существующих файла и каталога обновляется время."""
        node, _ = self.shell.vfs.resolve("/etc/hostname", [])
        node.mtime = DOS_EPOCH
        self.run_cmd("touch /etc/hostname /etc")
        self.assertGreater(node.mtime, DOS_EPOCH)
        self.assertEqual(node.data, b"host\n")

    def test_no_create(self):
        """``-c`` не создаёт отсутствующие файлы."""
        self.assertEqual(self.run_cmd("touch -c ghost"), (0, ""))
        self.assertFalse(self.exists("/ghost"))

    def test_errors(self):
        """Ошибки touch не мешают обработке остальных операндов."""
        status, err = self.run_cmd("touch /none/x /etc/hostname/x ok")
        self.assertEqual(status, 1)
        self.assertEqual(
            err, "touch: cannot touch '/none/x': No such file or directory\n"
            "touch: cannot touch '/etc/hostname/x': Not a directory\n")
        self.assertTrue(self.exists("/ok"))

    def test_usage_errors(self):
        """Нет операндов, неверная опция, путь со слешем на конце."""
        self.assertEqual(
            self.run_cmd("touch"), (1, "touch: missing file operand\n"))
        self.assertEqual(self.run_cmd("touch -z a")[0], 1)
        self.assertEqual(self.run_cmd("touch newdir/")[0], 1)


class RmTest(ModifyTestCase):
    """Команда rm."""

    def test_remove_files(self):
        """Файлы удаляются только в памяти."""
        self.run_cmd("cd /home/user")
        self.assertEqual(self.run_cmd("rm docs/a.txt /motd"), (0, ""))
        self.assertFalse(self.exists("/motd"))
        self.assertFalse(self.exists("/home/user/docs/a.txt"))
        self.assert_archive_unchanged()

    def test_remove_dir_requires_recursive(self):
        """Каталог удаляется только с ``-r`` или ``-R``."""
        self.assertEqual(
            self.run_cmd("rm /etc"),
            (1, "rm: cannot remove '/etc': Is a directory\n"))
        self.assertEqual(self.run_cmd("rm -r /etc"), (0, ""))
        self.assertEqual(self.run_cmd("rm -R /home/user/docs/sub"), (0, ""))
        self.assertFalse(self.exists("/etc"))
        self.assertFalse(self.exists("/home/user/docs/sub"))

    def test_force(self):
        """``-f`` скрывает только ошибки отсутствующих путей."""
        self.assertEqual(self.run_cmd("rm -f none"), (0, ""))
        self.assertEqual(self.run_cmd("rm -f"), (0, ""))
        self.assertEqual(
            self.run_cmd("rm -f /etc/hostname/"),
            (1, "rm: cannot remove '/etc/hostname/': Not a directory\n"))

    def test_remove_current_dir(self):
        """При удалении текущего каталога — переход в родителя."""
        self.run_cmd("cd /home/user/docs/sub")
        self.run_cmd("rm -r /home/user")
        self.assertEqual(self.shell.cwd, ["home"])

    def test_protected_paths(self):
        """Нельзя удалить корень, ``.`` и ``..``."""
        cases = {
            "rm -r /": "rm: it is dangerous to operate recursively on '/'\n",
            "rm /": "rm: cannot remove '/': Is a directory\n",
            "rm -r .": "rm: refusing to remove '.' or '..' directory: "
                       "skipping '.'\n",
            "rm -r etc/..": "rm: refusing to remove '.' or '..' "
                            "directory: skipping 'etc/..'\n",
        }
        for line, message in cases.items():
            with self.subTest(line=line):
                self.assertEqual(self.run_cmd(line), (1, message))
        self.assertTrue(self.exists("/etc"))

    def test_errors(self):
        """Ошибки rm не мешают обработке остальных операндов."""
        status, err = self.run_cmd("rm none /motd")
        self.assertEqual(status, 1)
        self.assertEqual(
            err, "rm: cannot remove 'none': No such file or directory\n")
        self.assertFalse(self.exists("/motd"))
        self.assertEqual(self.run_cmd("rm"), (1, "rm: missing operand\n"))
        self.assertEqual(self.run_cmd("rm -x a")[0], 1)


if __name__ == "__main__":
    unittest.main()
