"""Исключения и коды завершения эмулятора."""

STATUS_OK = 0
STATUS_ERROR = 1
STATUS_NOT_FOUND = 127
STATUS_INTERRUPTED = 130


class CommandError(Exception):
    """Ошибка выполнения команды; текст выводится пользователю."""


class ExitRequest(Exception):
    """Запрос на завершение работы эмулятора с заданным кодом."""

    def __init__(self, code):
        """Сохранить код завершения.

        :param code: код, с которым завершится эмулятор.
        """
        super().__init__(code)
        self.code = code
