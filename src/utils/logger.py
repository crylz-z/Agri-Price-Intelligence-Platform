import sys
import structlog
import logging
import os

def get_logger(name):
    """
    Configures and returns a structlog logger.
    
    In development (TTY detected), it uses ConsoleRenderer for colorful, human-readable logs.
    In production (No TTY), it uses JSONRenderer for structured logs suitable for observability tools.
    """
    
    # Configure shared processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.CallsiteParameterAdder(
            {
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            }
        ),
    ]

    # Determine environment
    if sys.stderr.isatty():
        # Local development: Human-readable
        processors.extend([
            structlog.dev.ConsoleRenderer()
        ])
    else:
        # Production: JSON
        processors.extend([
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ])

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True
    )

    log = structlog.get_logger(name)
    return log
