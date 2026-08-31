import logging

from config import settings

logger = logging.getLogger("ip-sakti.observability")


def configure_observability(app) -> None:
    if not settings.otel_enabled:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

        provider = TracerProvider(resource=Resource.create({"service.name": settings.otel_service_name}))
        exporter = (
            OTLPSpanExporter(endpoint=settings.otel_exporter_endpoint)
            if settings.otel_exporter_endpoint
            else ConsoleSpanExporter()
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
    except Exception:
        logger.exception("OpenTelemetry initialization failed")
        if settings.production:
            raise
