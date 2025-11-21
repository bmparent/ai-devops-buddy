"""Tools for correlating heuristic signals into crash alerts.

The correlator ingests raw heuristic module outputs, links triggers to
follow-on collapse/pump signals within a configurable window, annotates kernel
panic events, and renders a visual timeline for incident response teams.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Sequence

import matplotlib.pyplot as plt
import plotly.graph_objects as go


@dataclass
class Event:
    """A timestamped signal emitted by a heuristic module."""

    timestamp: float
    event_type: str
    source: str = "unknown"
    detail: dict = field(default_factory=dict)


@dataclass
class MetricSample:
    """A single telemetry sample capturing heat/entropy at a point in time."""

    timestamp: float
    thermal: float | None = None
    entropy: float | None = None


@dataclass
class CorrelationResult:
    """Correlation between a trigger event and subsequent signals."""

    trigger: Event
    correlated_signals: List[Event]
    kernel_panics: List[Event]
    window_end: float

    def to_dict(self) -> dict:
        return {
            "trigger": _event_to_dict(self.trigger),
            "signals": [_event_to_dict(signal) for signal in self.correlated_signals],
            "kernel_panics": [_event_to_dict(panic) for panic in self.kernel_panics],
            "window_end": self.window_end,
        }


def _event_to_dict(event: Event) -> dict:
    return {
        "timestamp": event.timestamp,
        "type": event.event_type,
        "source": event.source,
        "detail": event.detail,
    }


def load_dataset(path: Path) -> tuple[list[Event], list[MetricSample]]:
    """Load heuristic events and metrics from a JSON dataset file.

    The expected schema is::

        {
            "events": [
                {"timestamp": 0.0, "type": "trigger", "source": "heuristicA", "detail": {...}},
                {"timestamp": 1.5, "type": "collapse", "source": "heuristicB", "detail": {...}},
                {"timestamp": 2.0, "type": "kernel_panic", "source": "os", "detail": {...}},
            ],
            "metrics": [
                {"timestamp": 0.0, "thermal": 42.1, "entropy": 0.12},
                ...
            ]
        }

    Unknown keys are ignored.
    """

    with path.open() as f:
        payload = json.load(f)

    raw_events = payload.get("events", [])
    events = [
        Event(
            timestamp=float(item["timestamp"]),
            event_type=str(item.get("type", "")).lower(),
            source=item.get("source", "unknown"),
            detail=item.get("detail", {}),
        )
        for item in raw_events
        if "timestamp" in item
    ]

    raw_metrics = payload.get("metrics", [])
    metrics = [
        MetricSample(
            timestamp=float(sample["timestamp"]),
            thermal=(
                float(sample.get("thermal"))
                if sample.get("thermal") is not None
                else None
            ),
            entropy=(
                float(sample.get("entropy"))
                if sample.get("entropy") is not None
                else None
            ),
        )
        for sample in raw_metrics
        if "timestamp" in sample
    ]
    metrics.sort(key=lambda m: m.timestamp)
    events.sort(key=lambda e: e.timestamp)
    return events, metrics


def correlate_events(
    events: Iterable[Event], window_seconds: float = 5.0
) -> list[CorrelationResult]:
    """Correlate trigger events with downstream collapse/pump signals.

    Args:
        events: Iterable of :class:`Event` items.
        window_seconds: Sliding window size after a trigger to attach follow-on signals.

    Returns:
        Sorted list of :class:`CorrelationResult` items containing matched signals and
        kernel panic annotations.
    """

    sorted_events: list[Event] = sorted(events, key=lambda e: e.timestamp)
    triggers = [event for event in sorted_events if event.event_type == "trigger"]
    signals = [
        event for event in sorted_events if event.event_type in {"collapse", "pump"}
    ]
    panics = [event for event in sorted_events if event.event_type == "kernel_panic"]

    results: list[CorrelationResult] = []
    for trigger in triggers:
        window_end = trigger.timestamp + window_seconds
        correlated_signals = [
            signal
            for signal in signals
            if trigger.timestamp <= signal.timestamp <= window_end
        ]
        correlated_panics = [
            panic
            for panic in panics
            if trigger.timestamp <= panic.timestamp <= window_end
        ]
        results.append(
            CorrelationResult(
                trigger=trigger,
                correlated_signals=correlated_signals,
                kernel_panics=correlated_panics,
                window_end=window_end,
            )
        )
    return results


def _add_event_markers(ax, events: Sequence[Event], color: str, label: str) -> None:
    if not events:
        return
    ax.scatter(
        [event.timestamp for event in events],
        [0 for _ in events],
        marker="o",
        color=color,
        label=label,
        alpha=0.7,
    )


def render_timeline(
    metrics: Sequence[MetricSample],
    events: Sequence[Event],
    correlations: Sequence[CorrelationResult],
    output_dir: Path,
    png_name: str = "timeline.png",
    html_name: str = "timeline.html",
) -> tuple[Path, Path]:
    """Render Matplotlib/Plotly timelines showing spikes and crash points."""

    output_dir.mkdir(parents=True, exist_ok=True)

    # Matplotlib timeline (PNG)
    fig, ax = plt.subplots(figsize=(10, 5))
    timestamps = [sample.timestamp for sample in metrics]
    thermal_values = [sample.thermal for sample in metrics]
    entropy_values = [sample.entropy for sample in metrics]
    combined_values = [
        value for value in thermal_values + entropy_values if value is not None
    ]
    value_ceiling = max(combined_values) if combined_values else 1

    if any(value is not None for value in thermal_values):
        ax.plot(timestamps, thermal_values, label="Thermal", color="#ff7f0e")
    if any(value is not None for value in entropy_values):
        ax.plot(timestamps, entropy_values, label="Entropy", color="#1f77b4")

    trigger_events = [event for event in events if event.event_type == "trigger"]
    collapse_events = [event for event in events if event.event_type == "collapse"]
    pump_events = [event for event in events if event.event_type == "pump"]
    panic_events = [event for event in events if event.event_type == "kernel_panic"]

    _add_event_markers(ax, trigger_events, "#9467bd", "Trigger")
    _add_event_markers(ax, collapse_events, "#d62728", "Collapse")
    _add_event_markers(ax, pump_events, "#2ca02c", "Pump")
    _add_event_markers(ax, panic_events, "#000000", "Kernel Panic")

    for idx, correlation in enumerate(correlations):
        ax.axvspan(
            correlation.trigger.timestamp,
            correlation.window_end,
            color="#fde725",
            alpha=0.1,
            linestyle="--",
            label="Correlation Window" if idx == 0 else None,
        )

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Signal")
    ax.set_title("Thermal/Entropy Hockey Stick with Crash Points")
    ax.legend(loc="upper left", bbox_to_anchor=(1.05, 1))
    ax.grid(True, linestyle="--", alpha=0.3)
    fig.tight_layout()

    png_path = output_dir / png_name
    fig.savefig(png_path, dpi=200)
    plt.close(fig)

    # Plotly interactive timeline (HTML)
    plotly_fig = go.Figure()
    if any(value is not None for value in thermal_values):
        plotly_fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=thermal_values,
                name="Thermal",
                mode="lines",
                line=dict(color="#ff7f0e"),
            )
        )
    if any(value is not None for value in entropy_values):
        plotly_fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=entropy_values,
                name="Entropy",
                mode="lines",
                line=dict(color="#1f77b4"),
            )
        )

    def _add_plotly_markers(
        event_subset: Sequence[Event], color: str, name: str
    ) -> None:
        if not event_subset:
            return
        plotly_fig.add_trace(
            go.Scatter(
                x=[event.timestamp for event in event_subset],
                y=[0 for _ in event_subset],
                mode="markers",
                marker=dict(color=color, size=10),
                name=name,
                hovertext=[event.source for event in event_subset],
            )
        )

    _add_plotly_markers(trigger_events, "#9467bd", "Trigger")
    _add_plotly_markers(collapse_events, "#d62728", "Collapse")
    _add_plotly_markers(pump_events, "#2ca02c", "Pump")
    _add_plotly_markers(panic_events, "#000000", "Kernel Panic")

    for idx, correlation in enumerate(correlations):
        plotly_fig.add_shape(
            type="rect",
            x0=correlation.trigger.timestamp,
            x1=correlation.window_end,
            y0=0,
            y1=value_ceiling,
            fillcolor="rgba(253, 231, 37, 0.1)",
            line=dict(color="rgba(253, 231, 37, 0.3)", dash="dash"),
            layer="below",
        )
        plotly_fig.add_annotation(
            x=correlation.trigger.timestamp,
            y=value_ceiling,
            text=f"Trigger #{idx + 1}",
            showarrow=True,
            arrowhead=1,
        )

    plotly_fig.update_layout(
        title="Thermal/Entropy Hockey Stick with Crash Points",
        xaxis_title="Time (s)",
        yaxis_title="Signal",
        legend_orientation="h",
        margin=dict(l=40, r=40, t=80, b=40),
        template="plotly_white",
    )

    html_path = output_dir / html_name
    plotly_fig.write_html(html_path)
    return png_path, html_path
