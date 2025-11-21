"""Trigger phase transition heuristics for glyph and entropy anomalies."""
from __future__ import annotations

import collections
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


@dataclass
class GlyphAnomaly:
    """An anomalous text snippet preceding a watchdog escalation."""

    source: str
    text: str
    entropy: float
    repetition_ratio: float
    glyph_ratio: float
    timestamp: Optional[pd.Timestamp]


@dataclass
class TriggerPhaseTransition:
    """Aggregated detection result for a watchdog bug_type 210 event."""

    bug_event_time: pd.Timestamp
    anomalies: List[GlyphAnomaly]


def shannon_entropy(text: str) -> float:
    counts = collections.Counter(text)
    total = len(text)
    if total == 0:
        return 0.0
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def repetition_score(text: str) -> float:
    if not text:
        return 0.0
    counts = collections.Counter(text)
    most_common = counts.most_common(1)[0][1]
    return most_common / len(text)


def glyph_ratio(text: str) -> float:
    if not text:
        return 0.0
    exotic = sum(1 for ch in text if ord(ch) > 127)
    return exotic / len(text)


def _collect_text_entries(db_path: Path) -> List[Dict[str, object]]:
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    records: List[Dict[str, object]] = []
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            col_cursor = conn.execute(f"PRAGMA table_info('{table}')")
            text_columns = [row[1] for row in col_cursor if "TEXT" in row[2].upper()]
            if not text_columns:
                continue
            query = f"SELECT rowid as row_identifier, {', '.join(text_columns)} FROM {table}"
            try:
                for row in conn.execute(query):
                    for column in text_columns:
                        value = row[column]
                        if value:
                            records.append(
                                {
                                    "source": f"{db_path.name}:{table}.{column}",
                                    "text": str(value),
                                    "row_identifier": row["row_identifier"],
                                    "timestamp": None,
                                }
                            )
            except sqlite3.DatabaseError:
                continue
    finally:
        conn.close()
    return records


def _normalize_watchdog_events(events: object) -> pd.DataFrame:
    if isinstance(events, pd.DataFrame):
        df = events.copy()
    else:
        df = pd.DataFrame(events)
    if "timestamp" not in df.columns:
        raise ValueError("watchdog events must include a 'timestamp' column")
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])
    if "bug_type" in df.columns:
        df = df[df["bug_type"] == 210]
    return df.sort_values("timestamp")


def detect_trigger_phase_transition(
    sms_db_path: Path,
    knowledge_db_path: Path,
    watchdog_events: object,
    *,
    entropy_threshold: float = 3.5,
    repetition_threshold: float = 0.25,
    glyph_threshold: float = 0.20,
    lookback_seconds: int = 300,
) -> List[TriggerPhaseTransition]:
    """Detect glyph anomalies that precede watchdog bug_type 210 events."""

    sms_entries = _collect_text_entries(Path(sms_db_path))
    knowledge_entries = _collect_text_entries(Path(knowledge_db_path))
    combined_entries = sms_entries + knowledge_entries

    if not combined_entries:
        return []

    df = pd.DataFrame(combined_entries)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["entropy"] = df["text"].map(shannon_entropy)
    df["repetition"] = df["text"].map(repetition_score)
    df["glyph_ratio"] = df["text"].map(glyph_ratio)

    anomalies = df[
        (df["entropy"] >= entropy_threshold)
        | (df["repetition"] >= repetition_threshold)
        | (df["glyph_ratio"] >= glyph_threshold)
    ]

    watchdog_df = _normalize_watchdog_events(watchdog_events)
    findings: List[TriggerPhaseTransition] = []

    for _, event in watchdog_df.iterrows():
        window_start = event["timestamp"] - pd.Timedelta(seconds=lookback_seconds)
        window_end = event["timestamp"]
        window_anomalies = anomalies[
            (anomalies["timestamp"].isna())
            | ((anomalies["timestamp"] >= window_start) & (anomalies["timestamp"] <= window_end))
        ]
        if window_anomalies.empty:
            continue

        glyphs = [
            GlyphAnomaly(
                source=row["source"],
                text=row["text"],
                entropy=float(row["entropy"]),
                repetition_ratio=float(row["repetition"]),
                glyph_ratio=float(row["glyph_ratio"]),
                timestamp=row["timestamp"],
            )
            for row in window_anomalies.to_dict("records")
        ]
        findings.append(
            TriggerPhaseTransition(
                bug_event_time=event["timestamp"],
                anomalies=glyphs,
            )
        )

    return findings


__all__ = [
    "GlyphAnomaly",
    "TriggerPhaseTransition",
    "detect_trigger_phase_transition",
    "shannon_entropy",
    "repetition_score",
    "glyph_ratio",
]
