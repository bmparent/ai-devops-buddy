"""Analysis package for correlating heuristic outputs."""

from .correlator import (
    CorrelationResult,
    Event,
    MetricSample,
    correlate_events,
    load_dataset,
    render_timeline,
)

__all__ = [
    "CorrelationResult",
    "Event",
    "MetricSample",
    "correlate_events",
    "load_dataset",
    "render_timeline",
]
