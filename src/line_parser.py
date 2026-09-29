"""Разбор строки ввода на команду и аргументы."""

COMMENT_PREFIX = "#"


def parse_line(line):
    """Разделить строку на имя команды и аргументы по пробелам.

    Слово, начинающееся с ``#``, открывает комментарий: оно и все
    следующие слова отбрасываются, как в UNIX-оболочках.

    :param line: строка, введённая пользователем.
    :return: кортеж ``(команда, аргументы)``; для пустой строки
        команда равна ``None``.
    """
    words = []
    for word in line.split():
        if word.startswith(COMMENT_PREFIX):
            break
        words.append(word)
    if not words:
        return None, []
    return words[0], words[1:]
