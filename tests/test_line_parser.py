"""Тесты разбора строки ввода."""

import unittest

from line_parser import parse_line


class ParseLineTest(unittest.TestCase):
    """Проверки функции :func:`parse_line`."""

    def test_empty_line(self):
        """Пустая строка не содержит команды."""
        self.assertEqual(parse_line(""), (None, []))

    def test_only_spaces(self):
        """Строка из пробелов не содержит команды."""
        self.assertEqual(parse_line("   \t  "), (None, []))

    def test_command_without_args(self):
        """Команда без аргументов."""
        self.assertEqual(parse_line("ls"), ("ls", []))

    def test_command_with_args(self):
        """Аргументы разделяются любым числом пробелов."""
        self.assertEqual(
            parse_line("  cd   /home\tuser  "), ("cd", ["/home", "user"]))

    def test_comment_line(self):
        """Строка-комментарий не содержит команды."""
        self.assertEqual(parse_line("# comment"), (None, []))

    def test_trailing_comment(self):
        """Комментарий в конце строки отбрасывается."""
        self.assertEqual(parse_line("ls -l # list"), ("ls", ["-l"]))

    def test_hash_inside_word(self):
        """Символ ``#`` внутри слова не начинает комментарий."""
        self.assertEqual(parse_line("cd a#b"), ("cd", ["a#b"]))


if __name__ == "__main__":
    unittest.main()
