class EmptyAPIResponseError(Exception):
    """Отсутствие ожидаемых ключей в ответе API."""

class MissingRequiredVarsError(Exception):
    """Отсутсвуют неоьходимые переменные."""

class ApiConnectionError(Exception):
    """Ошибка полученгия ответа от API."""

class IncorrectDataReceivedError(Exception):
    """Ошибка несоответствия полученных данных ожидаемым."""