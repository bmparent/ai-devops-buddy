"""Detection for parasitic pump-like thermal inefficiencies."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import List, Optional

import pandas as pd


@dataclass
class ParasiticPumpAlert:
    """Structured result describing a parasitic pump detection."""

    start: dt.datetime
    end: dt.datetime
    ter_peak: float
    samples: int


def detect_parasitic_pump(
    events_df: object,
    *,
    ter_threshold: float = 5.0,
    io_floor: float = 1.0,
    sustain_seconds: int = 10,
) -> List[ParasiticPumpAlert]:
    """Identify sustained periods of high thermodynamic inefficiency.

    A parasitic pump manifests as a high Thermodynamic Efficiency Ratio (TER)
    while both disk and network I/O stay near zero. The function evaluates a
    pandas ``DataFrame`` with at least ``timestamp``, ``thermal_pressure``,
    ``ram_growth``, ``disk_io``, and ``net_io`` columns.
    """

    df = events_df.copy() if isinstance(events_df, pd.DataFrame) else pd.DataFrame(events_df)
    if "timestamp" not in df.columns:
        raise ValueError("events_df must include a 'timestamp' column")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])

    for field in ("thermal_pressure", "ram_growth", "disk_io", "net_io"):
        if field not in df.columns:
            raise ValueError(f"events_df missing required column: {field}")

    df["io_activity"] = df["disk_io"].fillna(0) + df["net_io"].fillna(0)
    df["ter"] = (
        df["thermal_pressure"].fillna(0) + df["ram_growth"].fillna(0)
    ) / (df["io_activity"] + 1e-6)
    df = df.sort_values("timestamp")

    alerts: List[ParasiticPumpAlert] = []
    streak_start: Optional[dt.datetime] = None
    last_ts: Optional[dt.datetime] = None
    tracked: List[float] = []

    for row in df.to_dict("records"):
        ts = row["timestamp"]
        flagged = row["ter"] >= ter_threshold and row["io_activity"] <= io_floor
        if flagged:
            if streak_start is None:
                streak_start = ts
                tracked = []
                last_ts = ts
            elif last_ts is not None:
                elapsed = (ts - last_ts).total_seconds()
                if elapsed > 5 * sustain_seconds:
                    # break in sampling cadence; restart accumulation
                    streak_start = ts
                    tracked = []
            tracked.append(row["ter"])
            last_ts = ts

            if streak_start and (ts - streak_start).total_seconds() >= sustain_seconds:
                alerts.append(
                    ParasiticPumpAlert(
                        start=streak_start,
                        end=ts,
                        ter_peak=max(tracked) if tracked else row["ter"],
                        samples=len(tracked),
                    )
                )
                streak_start = None
                tracked = []
        else:
            streak_start = None
            tracked = []
            last_ts = ts

    return alerts


__all__ = ["ParasiticPumpAlert", "detect_parasitic_pump"]
