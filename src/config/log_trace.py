import sys


def current_trace_id() -> str:
    """
    trace_id текущего запроса (32 hex-символа) или "-" вне запроса.
    Пакет opentelemetry не импортируется: если трассировка не запущена,
    его нет в sys.modules и результат всегда "-".
    """
    trace = sys.modules.get("opentelemetry.trace")
    if trace is None:
        return "-"
    ctx = trace.get_current_span().get_span_context()
    return format(ctx.trace_id, "032x") if ctx.is_valid else "-"


def add_trace_id(record) -> None:
    """Patcher для loguru: кладёт trace_id в record["extra"]."""
    record["extra"]["trace_id"] = current_trace_id()
