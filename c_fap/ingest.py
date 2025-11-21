"""Utilities for streaming ingestion of iOS/macOS forensic artifacts.

The functions in this module avoid loading entire files into memory. Tarballs
are walked lazily, text logs are streamed line-by-line, and SQLite databases are
read in configurable batches. The resulting :class:`EventRecord` instances
normalize disparate sources into comparable event metrics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
import importlib.util
import io
import json
import re
import sqlite3
import tarfile
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Optional

__all__ = [
    "EventRecord",
    "iter_crash_ips",
    "iter_sysdiagnose_tarball",
    "iter_knowledgec_events",
    "iter_sms_events",
]


@dataclass
class EventRecord:
    """Normalized event row across crash logs, sysdiagnose bundles, and SQLite.

    Attributes
    ----------
    timestamp:
        Datetime associated with the event. If no timezone is present in the
        source data, UTC is assumed.
    source_file:
        Name of the originating artifact (file inside a tarball, crash log, or
        SQLite database).
    pid:
        Process identifier when available.
    cpu, ram, thermal, disk, network:
        Optional numeric metrics extracted from the source.
    context:
        Additional metadata specific to the parsed source.
    """

    timestamp: datetime
    source_file: str
    pid: Optional[int] = None
    cpu: Optional[float] = None
    ram: Optional[float] = None
    thermal: Optional[float] = None
    disk: Optional[float] = None
    network: Optional[float] = None
    context: Dict[str, Any] = field(default_factory=dict)


_TIMESTAMP_RE = re.compile(r"(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)")
_PID_RE = re.compile(r"pid(?:\s*|=|:)(?P<pid>\d+)", re.IGNORECASE)
_CPU_RE = re.compile(r"cpu(?:_|\s)usage[:=]\s*(?P<cpu>[-+]?\d*\.\d+|\d+)", re.IGNORECASE)
_RAM_RE = re.compile(r"(?:ram|memory)(?:_|\s)(?:usage|pressure)[:=]\s*(?P<ram>[-+]?\d*\.\d+|\d+)", re.IGNORECASE)
_THERMAL_RE = re.compile(r"thermal(?:_|\s)(?:level|state|pressure)[:=]\s*(?P<thermal>[-+]?\d*\.\d+|\d+)", re.IGNORECASE)
_DISK_RE = re.compile(r"disk(?:_|\s)(?:usage|pressure)[:=]\s*(?P<disk>[-+]?\d*\.\d+|\d+)", re.IGNORECASE)
_NETWORK_RE = re.compile(r"network(?:_|\s)(?:usage|throughput)[:=]\s*(?P<network>[-+]?\d*\.\d+|\d+)", re.IGNORECASE)


def _get_timestamp_from_text(text: str) -> Optional[datetime]:
    match = _TIMESTAMP_RE.search(text)
    if not match:
        return None
    raw = match.group(1)
    try:
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def _coerce_float(value: str) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _read_text(member: tarfile.TarInfo, tar: tarfile.TarFile) -> Iterable[str]:
    extracted = tar.extractfile(member)
    if not extracted:
        return []
    wrapper = io.TextIOWrapper(extracted, encoding="utf-8", errors="ignore")
    return wrapper


def iter_crash_ips(path: str | Path) -> Iterator[EventRecord]:
    """Yield :class:`EventRecord` entries from a crash ``.ips`` log.

    The reader scans the file incrementally to avoid large allocations. Both
    JSON-formatted and key/value logs are supported through lightweight regex
    extraction.
    """

    source = str(path)
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        buffer: list[str] = []
        for line in handle:
            stripped = line.strip()
            if stripped:
                buffer.append(stripped)
            if stripped.endswith("}") and buffer and buffer[0].startswith("{"):
                try:
                    payload = json.loads("".join(buffer))
                except json.JSONDecodeError:
                    payload = {}
                buffer.clear()
                ts = payload.get("timestamp")
                pid = payload.get("pid") or payload.get("proc_pid")
                timestamp = _get_timestamp_from_text(str(ts)) or datetime.now(timezone.utc)
                yield EventRecord(
                    timestamp=timestamp,
                    source_file=source,
                    pid=int(pid) if pid is not None else None,
                    cpu=_coerce_float(payload.get("cpuUsage") or payload.get("cpu_usage")),
                    ram=_coerce_float(payload.get("memoryUsage") or payload.get("ram_usage")),
                    thermal=_coerce_float(payload.get("thermalLevel")),
                    disk=None,
                    network=None,
                    context={k: v for k, v in payload.items() if k not in {"timestamp", "pid"}},
                )
            else:
                timestamp = _get_timestamp_from_text(stripped)
                if not timestamp:
                    continue
                pid_match = _PID_RE.search(stripped)
                cpu_match = _CPU_RE.search(stripped)
                ram_match = _RAM_RE.search(stripped)
                thermal_match = _THERMAL_RE.search(stripped)
                disk_match = _DISK_RE.search(stripped)
                network_match = _NETWORK_RE.search(stripped)
                yield EventRecord(
                    timestamp=timestamp,
                    source_file=source,
                    pid=int(pid_match.group("pid")) if pid_match else None,
                    cpu=_coerce_float(cpu_match.group("cpu")) if cpu_match else None,
                    ram=_coerce_float(ram_match.group("ram")) if ram_match else None,
                    thermal=_coerce_float(thermal_match.group("thermal")) if thermal_match else None,
                    disk=_coerce_float(disk_match.group("disk")) if disk_match else None,
                    network=_coerce_float(network_match.group("network")) if network_match else None,
                    context={"line": stripped},
                )


def _parse_vm_stat(member: tarfile.TarInfo, tar: tarfile.TarFile) -> Iterator[EventRecord]:
    page_size = 4096
    timestamp = datetime.fromtimestamp(member.mtime, tz=timezone.utc)
    for line in _read_text(member, tar):
        if "page size of" in line:
            size_match = re.search(r"page size of (\d+)", line)
            if size_match:
                page_size = int(size_match.group(1))
            continue
        if not line.strip():
            continue
        if ":" not in line:
            continue
        key, raw_value = [piece.strip().strip(".") for piece in line.split(":", 1)]
        pages = _coerce_float(raw_value)
        if pages is None:
            continue
        ram_bytes = pages * page_size
        yield EventRecord(
            timestamp=timestamp,
            source_file=member.name,
            ram=ram_bytes,
            context={"metric": key, "pages": pages, "page_size": page_size},
        )


def _parse_thermalmonitord(member: tarfile.TarInfo, tar: tarfile.TarFile) -> Iterator[EventRecord]:
    for line in _read_text(member, tar):
        ts = _get_timestamp_from_text(line)
        thermal_match = re.search(r"([+-]?\d+\.\d+)\s*C", line)
        pid_match = _PID_RE.search(line)
        if not ts and member.mtime:
            ts = datetime.fromtimestamp(member.mtime, tz=timezone.utc)
        if not ts:
            continue
        yield EventRecord(
            timestamp=ts,
            source_file=member.name,
            pid=int(pid_match.group("pid")) if pid_match else None,
            thermal=_coerce_float(thermal_match.group(1)) if thermal_match else None,
            context={"line": line.strip()},
        )


def _parse_powerd(member: tarfile.TarInfo, tar: tarfile.TarFile) -> Iterator[EventRecord]:
    for line in _read_text(member, tar):
        ts = _get_timestamp_from_text(line)
        if not ts and member.mtime:
            ts = datetime.fromtimestamp(member.mtime, tz=timezone.utc)
        if not ts:
            continue
        battery_match = re.search(r"([+-]?\d+\.\d+|\d+)%", line)
        cpu_match = _CPU_RE.search(line)
        thermal_match = _THERMAL_RE.search(line)
        yield EventRecord(
            timestamp=ts,
            source_file=member.name,
            cpu=_coerce_float(cpu_match.group("cpu")) if cpu_match else None,
            thermal=_coerce_float(thermal_match.group("thermal")) if thermal_match else None,
            context={"line": line.strip(), "battery_percent": _coerce_float(battery_match.group(1)) if battery_match else None},
        )


def iter_sysdiagnose_tarball(path: str | Path) -> Iterator[EventRecord]:
    """Stream relevant files from a sysdiagnose tarball.

    Only the heavy hitters (``vm_stat``, ``thermalmonitord``, ``powerd``) are
    parsed to avoid excessive IO. The tar archive is iterated member by member,
    keeping memory usage constant.
    """

    with tarfile.open(path, mode="r:*") as tar:
        for member in tar:
            if not member.isfile():
                continue
            name = member.name.lower()
            if "vm_stat" in name:
                yield from _parse_vm_stat(member, tar)
            elif "thermalmonitord" in name:
                yield from _parse_thermalmonitord(member, tar)
            elif "powerd" in name:
                yield from _parse_powerd(member, tar)


def _get_pandas():
    if importlib.util.find_spec("pandas"):
        import pandas as pd  # type: ignore

        return pd
    return None


def _get_polars():
    if importlib.util.find_spec("polars"):
        import polars as pl  # type: ignore

        return pl
    return None


def _convert_apple_epoch(value: float) -> datetime:
    # Apple Cocoa epoch starts at 2001-01-01
    apple_epoch_start = datetime(2001, 1, 1, tzinfo=timezone.utc)
    return apple_epoch_start + timedelta(seconds=value)


def iter_knowledgec_events(db_path: str | Path, chunk_size: int = 500) -> Iterator[EventRecord]:
    """Yield KnowledgeC usage events from SQLite using chunked reads."""

    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as sqlite_conn:
        sqlite_conn.row_factory = sqlite3.Row
        pd = _get_pandas()
        if pd:
            for frame in pd.read_sql_query(
                "SELECT startDate, process, pid, cpuTime, bundleID FROM ZOBJECT", sqlite_conn, chunksize=chunk_size
            ):
                for _, row in frame.iterrows():
                    timestamp = _convert_apple_epoch(row["startDate"])
                    yield EventRecord(
                        timestamp=timestamp,
                        source_file=str(db_path),
                        pid=int(row["pid"]) if not pd.isna(row["pid"]) else None,
                        cpu=_coerce_float(row["cpuTime"]),
                        context={"process": row["process"], "bundle": row["bundleID"]},
                    )
            return

        polars = _get_polars()
        if polars:
            for frame in polars.read_database_uri(
                f"file:{db_path}?mode=ro",
                query="SELECT startDate, process, pid, cpuTime, bundleID FROM ZOBJECT",
                batch_size=chunk_size,
            ).iter_rows(named=True):
                timestamp = _convert_apple_epoch(frame["startDate"])
                yield EventRecord(
                    timestamp=timestamp,
                    source_file=str(db_path),
                    pid=int(frame["pid"]) if frame["pid"] is not None else None,
                    cpu=_coerce_float(frame["cpuTime"]),
                    context={"process": frame["process"], "bundle": frame["bundleID"]},
                )
            return

        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT startDate, process, pid, cpuTime, bundleID FROM ZOBJECT")
        while rows := cursor.fetchmany(chunk_size):
            for start_date, process, pid, cpu_time, bundle_id in rows:
                timestamp = _convert_apple_epoch(float(start_date))
                yield EventRecord(
                    timestamp=timestamp,
                    source_file=str(db_path),
                    pid=int(pid) if pid is not None else None,
                    cpu=_coerce_float(cpu_time),
                    context={"process": process, "bundle": bundle_id},
                )


def iter_sms_events(db_path: str | Path, chunk_size: int = 500) -> Iterator[EventRecord]:
    """Yield SMS send/receive events from the messages database in chunks."""

    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as sqlite_conn:
        sqlite_conn.row_factory = sqlite3.Row
        pd = _get_pandas()
        if pd:
            for frame in pd.read_sql_query(
                "SELECT date, is_from_me, handle_id FROM message",
                sqlite_conn,
                chunksize=chunk_size,
            ):
                for _, row in frame.iterrows():
                    timestamp = _convert_apple_epoch(row["date"])
                    yield EventRecord(
                        timestamp=timestamp,
                        source_file=str(db_path),
                        context={"direction": "outgoing" if row["is_from_me"] else "incoming", "handle_id": row["handle_id"]},
                    )
            return

        polars = _get_polars()
        if polars:
            for row in polars.read_database_uri(
                f"file:{db_path}?mode=ro",
                query="SELECT date, is_from_me, handle_id FROM message",
                batch_size=chunk_size,
            ).iter_rows(named=True):
                timestamp = _convert_apple_epoch(row["date"])
                yield EventRecord(
                    timestamp=timestamp,
                    source_file=str(db_path),
                    context={"direction": "outgoing" if row["is_from_me"] else "incoming", "handle_id": row["handle_id"]},
                )
            return

        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT date, is_from_me, handle_id FROM message")
        while rows := cursor.fetchmany(chunk_size):
            for date_value, is_from_me, handle_id in rows:
                timestamp = _convert_apple_epoch(float(date_value))
                yield EventRecord(
                    timestamp=timestamp,
                    source_file=str(db_path),
                    context={"direction": "outgoing" if is_from_me else "incoming", "handle_id": handle_id},
                )
