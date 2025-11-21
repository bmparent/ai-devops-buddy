"""Timeline normalization utilities."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, MutableMapping, Sequence

try:  # pragma: no cover - optional dependency
    import pandas as pd
except Exception:  # pragma: no cover - avoid hard dependency
    pd = None

try:  # pragma: no cover - optional dependency
    import polars as pl
except Exception:  # pragma: no cover - avoid hard dependency
    pl = None


def _ensure_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_datetime_string(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Unsupported datetime string: {value}") from exc
    return _ensure_datetime(parsed)


class TimelineNormalizer:
    """Normalize heterogeneous ingest timestamps into a unified timeline.

    The normalizer understands several time bases commonly encountered in
    endpoint telemetry. It converts every event into a UTC-based timestamp with
    microsecond precision and returns either a pandas ``DataFrame`` or polars
    ``DataFrame`` sorted (and indexed for pandas) by the normalized timestamp.
    """

    MAC_ABSOLUTE_OFFSET = 978_307_200.0

    def __init__(
        self,
        boot_time: datetime | None = None,
        prefer_backend: str | None = None,
    ) -> None:
        """Create a new normalizer.

        Args:
            boot_time: Optional boot time for uptime-based clocks. If provided
                without timezone info, UTC is assumed.
            prefer_backend: Optional backend override (``"pandas"`` or
                ``"polars"``). If omitted, the first available backend is used.
        """

        self.boot_time = _ensure_datetime(boot_time) if boot_time else None
        self.prefer_backend = prefer_backend

    def normalize_batch(
        self,
        events: Iterable[Mapping[str, Any]],
        prefer_backend: str | None = None,
    ) -> Any:
        """Normalize a batch of ingest events.

        Each event is expected to expose ``timestamp`` and ``time_base`` keys.
        Supported time bases include:

        ``epoch``
            Seconds since the Unix epoch.
        ``mac_absolute``
            Seconds since the macOS absolute time epoch (2001-01-01). The
            ``MAC_ABSOLUTE_OFFSET`` accounts for the difference to Unix time.
        ``uptime``
            Seconds since boot. A boot time must be provided on the instance or
            on the event itself via ``boot_time``.
        ``iso8601``
            Any ISO-8601 string parseable by :meth:`datetime.fromisoformat`.

        The output ``DataFrame`` is sorted by ``normalized_timestamp`` and, when
        using pandas, indexed by that column.
        """

        normalized_rows = [self.normalize_event(event) for event in events]
        backend = self._choose_backend(prefer_backend)
        if backend == "pandas":
            return self._to_pandas(normalized_rows)
        return self._to_polars(normalized_rows)

    def normalize_event(self, event: Mapping[str, Any]) -> MutableMapping[str, Any]:
        """Normalize a single event and preserve original metadata."""

        time_base = event.get("time_base", "epoch")
        raw_timestamp = event.get("timestamp")
        unit = event.get("unit")
        boot_time = event.get("boot_time") or self.boot_time
        if time_base == "uptime" and boot_time is None:
            raise ValueError("boot_time is required for uptime-based events")

        normalized_ts = self._normalize_timestamp(
            raw_timestamp, time_base=time_base, unit=unit, boot_time=boot_time
        )

        normalized_event: MutableMapping[str, Any] = dict(event)
        normalized_event["normalized_timestamp"] = normalized_ts
        return normalized_event

    def _normalize_timestamp(
        self,
        raw_timestamp: Any,
        *,
        time_base: str,
        unit: str | None = None,
        boot_time: datetime | None = None,
    ) -> datetime:
        if raw_timestamp is None:
            raise ValueError("timestamp is required")

        base = time_base.lower()
        if base == "iso8601":
            return _parse_datetime_string(str(raw_timestamp))

        seconds = self._to_seconds(raw_timestamp, unit=unit)
        if base == "epoch":
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        if base == "mac_absolute":
            return datetime.fromtimestamp(
                seconds + self.MAC_ABSOLUTE_OFFSET, tz=timezone.utc
            )
        if base == "uptime":
            if boot_time is None:
                raise ValueError("boot_time is required for uptime-based events")
            boot = _ensure_datetime(boot_time)
            normalized = boot + timedelta(seconds=seconds)
            return normalized.astimezone(timezone.utc)

        raise ValueError(f"Unsupported time base: {time_base}")

    @staticmethod
    def _to_seconds(value: Any, unit: str | None = None) -> float:
        """Coerce a timestamp in arbitrary units to seconds."""

        if isinstance(value, datetime):
            return _ensure_datetime(value).timestamp()
        if isinstance(value, str) and unit is None:
            return _parse_datetime_string(value).timestamp()

        if unit:
            factor = TimelineNormalizer._unit_divisor(unit)
            return float(value) / factor

        numeric = float(value)
        magnitude = abs(numeric)
        if magnitude >= 1e18:  # nanoseconds from epoch
            return numeric / 1e9
        if magnitude >= 1e15:  # microseconds from epoch
            return numeric / 1e6
        if magnitude >= 1e12:  # milliseconds from epoch
            return numeric / 1e3
        return numeric

    @staticmethod
    def _unit_divisor(unit: str) -> float:
        normalized = unit.lower()
        if normalized in {"s", "sec", "secs", "second", "seconds"}:
            return 1.0
        if normalized in {"ms", "millisecond", "milliseconds"}:
            return 1e3
        if normalized in {"us", "microsecond", "microseconds"}:
            return 1e6
        if normalized in {"ns", "nanosecond", "nanoseconds"}:
            return 1e9
        raise ValueError(f"Unsupported time unit: {unit}")

    def _choose_backend(self, prefer_backend: str | None = None) -> str:
        preferred = prefer_backend or self.prefer_backend
        candidates: Sequence[str]
        if preferred:
            candidates = (preferred,)
        else:
            candidates = ("pandas", "polars")

        for candidate in candidates:
            if candidate == "pandas" and pd is not None:
                return "pandas"
            if candidate == "polars" and pl is not None:
                return "polars"

        raise RuntimeError(
            "No suitable DataFrame backend available. Install pandas or polars"
        )

    def _to_pandas(self, rows: list[MutableMapping[str, Any]]):
        if pd is None:  # pragma: no cover - guarded by _choose_backend
            raise RuntimeError("pandas is not available")

        df = pd.DataFrame(rows)
        df["normalized_timestamp"] = pd.to_datetime(
            df["normalized_timestamp"], utc=True
        )
        df = df.sort_values("normalized_timestamp")
        return df.set_index("normalized_timestamp")

    def _to_polars(self, rows: list[MutableMapping[str, Any]]):
        if pl is None:  # pragma: no cover - guarded by _choose_backend
            raise RuntimeError("polars is not available")

        df = pl.from_dicts(rows)
        if "normalized_timestamp" in df.columns:
            df = df.with_columns(
                pl.col("normalized_timestamp").cast(
                    pl.Datetime(time_unit="us", time_zone="UTC")
                )
            )
            df = df.sort("normalized_timestamp")
        return df


__all__ = ["TimelineNormalizer"]
