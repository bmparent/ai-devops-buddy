"""Detection logic for memory compression saturation events."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Iterable, List, MutableMapping, Optional

import pandas as pd


@dataclass
class VectorCollapseAlert:
    """Alert structure for vector-collapse style pressure events."""

    pid: int
    start: dt.datetime
    end: dt.datetime
    mean_compression_ratio: float
    peak_cpu_utilization: float


class VectorCollapseDetector:
    """Detects sustained memory compression at high CPU usage.

    The detector examines per-PID swap or ``vm_stat`` style logs for
    the ratio of compressed bytes to total paging activity. When the
    compression ratio stays above ``compression_threshold`` while CPU
    utilization also exceeds ``cpu_threshold`` for at least
    ``duration_seconds``, an alert is emitted.
    """

    def __init__(
        self,
        compression_threshold: float = 0.85,
        cpu_threshold: float = 0.80,
        duration_seconds: int = 10,
    ) -> None:
        self.compression_threshold = compression_threshold
        self.cpu_threshold = cpu_threshold
        self.duration_seconds = duration_seconds

    def _coerce_dataframe(self, payload: object, *, name: str) -> pd.DataFrame:
        if isinstance(payload, pd.DataFrame):
            return payload.copy()
        if isinstance(payload, str):
            return pd.read_csv(payload)
        if isinstance(payload, Iterable):
            return pd.DataFrame(payload)
        raise TypeError(f"Unsupported {name} payload type: {type(payload)!r}")

    def _prepare_time(self, df: pd.DataFrame) -> pd.DataFrame:
        if "timestamp" not in df.columns:
            raise ValueError("input data must contain a 'timestamp' column")
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp"])
        return df

    def _inject_compression_ratio(self, df: pd.DataFrame) -> pd.DataFrame:
        if "compression_ratio" in df.columns:
            return df
        required = {"compressed_bytes", "swap_in_bytes", "swap_out_bytes"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(
                "compression_ratio missing and could not be derived; "
                f"required columns: {sorted(required)}"
            )
        denominator = df[list(required)].sum(axis=1)
        df["compression_ratio"] = df["compressed_bytes"] / denominator.replace(0, 1)
        return df

    def _inject_cpu(self, df: pd.DataFrame) -> pd.DataFrame:
        if "cpu_utilization" in df.columns:
            return df
        raise ValueError("CPU samples must include a 'cpu_utilization' column")

    def detect(
        self,
        vm_swap_logs: object,
        cpu_samples: object,
    ) -> List[VectorCollapseAlert]:
        """Detect vector collapse events.

        Parameters
        ----------
        vm_swap_logs:
            Any object convertible to a pandas ``DataFrame`` containing per-PID
            swap or compression metrics. A ``compression_ratio`` column can be
            supplied directly or derived from ``compressed_bytes``,
            ``swap_in_bytes``, and ``swap_out_bytes``.
        cpu_samples:
            Any object convertible to a pandas ``DataFrame`` containing per-PID
            CPU utilization samples with columns ``pid``, ``timestamp``, and
            ``cpu_utilization`` in the range ``[0, 1]``.
        """

        vm_df = self._coerce_dataframe(vm_swap_logs, name="vm_swap_logs")
        cpu_df = self._coerce_dataframe(cpu_samples, name="cpu_samples")
        vm_df = self._prepare_time(vm_df)
        cpu_df = self._prepare_time(cpu_df)
        vm_df = self._inject_compression_ratio(vm_df)
        cpu_df = self._inject_cpu(cpu_df)

        merged = vm_df.merge(cpu_df, on=["pid", "timestamp"], how="inner")
        merged = merged.sort_values(["pid", "timestamp"]).reset_index(drop=True)

        alerts: List[VectorCollapseAlert] = []
        for pid, group in merged.groupby("pid"):
            group = group.sort_values("timestamp")
            mask = (
                group["compression_ratio"] >= self.compression_threshold
            ) & (group["cpu_utilization"] >= self.cpu_threshold)
            if not mask.any():
                continue

            streak_start: Optional[dt.datetime] = None
            last_ts: Optional[dt.datetime] = None
            accumulator = 0.0
            tracked_rows: List[MutableMapping[str, float]] = []

            for flagged, row in zip(mask.tolist(), group.to_dict("records")):
                ts = row["timestamp"]
                if flagged:
                    if streak_start is None:
                        streak_start = ts
                        accumulator = 0.0
                        tracked_rows = []
                    elif last_ts is not None:
                        accumulator += (ts - last_ts).total_seconds()
                    tracked_rows.append(row)

                    if accumulator >= self.duration_seconds:
                        alerts.append(
                            VectorCollapseAlert(
                                pid=int(pid),
                                start=streak_start,
                                end=ts,
                                mean_compression_ratio=float(
                                    sum(r["compression_ratio"] for r in tracked_rows)
                                    / len(tracked_rows)
                                ),
                                peak_cpu_utilization=float(
                                    max(r["cpu_utilization"] for r in tracked_rows)
                                ),
                            )
                        )
                        streak_start = None
                        tracked_rows = []
                        accumulator = 0.0
                else:
                    streak_start = None
                    tracked_rows = []
                    accumulator = 0.0
                last_ts = ts

        return alerts


def detect_vector_collapse(
    vm_swap_logs: object,
    cpu_samples: object,
    *,
    compression_threshold: float = 0.85,
    cpu_threshold: float = 0.80,
    duration_seconds: int = 10,
) -> List[VectorCollapseAlert]:
    """Convenience wrapper around :class:`VectorCollapseDetector`."""

    detector = VectorCollapseDetector(
        compression_threshold=compression_threshold,
        cpu_threshold=cpu_threshold,
        duration_seconds=duration_seconds,
    )
    return detector.detect(vm_swap_logs=vm_swap_logs, cpu_samples=cpu_samples)


__all__ = [
    "VectorCollapseAlert",
    "VectorCollapseDetector",
    "detect_vector_collapse",
]
