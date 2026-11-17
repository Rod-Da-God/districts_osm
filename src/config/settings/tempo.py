from pydantic import Field

from config.settings.base import BaseAppSettings


class TempoSettings(BaseAppSettings):
    otel_sdk_disabled: bool = Field(default=False)
    otel_service_name: str = Field(default="backend1")
    otel_exporter_otlp_endpoint: str = Field(default="http://tempo.monitoring.svc:4318")
    otel_exporter_otlp_protocol: str = Field(default="http/protobuf")
    otel_traces_sampler: str = Field(default="parentbased_traceidratio")
    otel_traces_sampler_arg: float = Field(default=1.0)
    otel_resource_attributes: str = Field(default="service.namespace=demo")
    otel_python_fastapi_excluded_urls: str = Field(default="health,metrics")

    otel_bsp_max_queue_size: int = Field(default=2048)
    otel_bsp_max_export_batch_size: int = Field(default=512)
    otel_bsp_schedule_delay_ms: int = Field(default=5000)
    otel_exporter_otlp_timeout: int = Field(
        default=3, description="таймаут экспорта в секундах"
    )
