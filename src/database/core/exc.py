class DBConnectException(Exception):
    """Базовое исключение для всех ошибок, связанных с подключением к БД."""

    pass


class NotFoundError(DBConnectException):
    """Исключение возникает когда запрашиваемые данные не найдены в БД."""

    pass


class EmptyFilterError(DBConnectException):
    """Исключение возникает когда переданы пустые фильтры для запроса."""

    pass


class InvalidFieldError(DBConnectException):
    """Исключение: указано невалидное или несуществующее поле."""

    pass


class EmptyValueError(DBConnectException):
    """Исключение: передано пустое значение обязательного поля."""

    pass


class UnknowAggregationFunc(DBConnectException):
    """Исключение возникает когда указана неизвестная агрегационная функция."""

    pass
