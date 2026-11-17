import uvicorn

from config import settings
from config.log_conf import setup_logging
from config.tracing import setup_tracing

setup_logging()
setup_tracing()

if __name__ == "__main__":
    # Приложение передаётся строкой: uvicorn импортирует app.py только здесь,
    uvicorn.run(
        "app:create_app",
        factory=True,
        host=settings.api.host,
        port=settings.api.port,
        log_level=settings.api.uc_log_level,
    )
