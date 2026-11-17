from types import ModuleType

from districts import service as districts_service


def get_districts_service() -> ModuleType:
    """
    Dependency для получения сервиса districts.

    Returns:
        service module
    """
    return districts_service
