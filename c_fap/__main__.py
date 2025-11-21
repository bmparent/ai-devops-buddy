"""CLI entrypoint for correlating heuristic module outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from c_fap.analysis import correlate_events, load_dataset, render_timeline


def _write_alerts(
    correlations, output_dir: Path, filename: str = "alerts.json"
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    alert_path = output_dir / filename
    with alert_path.open("w") as f:
        json.dump([corr.to_dict() for corr in correlations], f, indent=2)
    return alert_path


def run(dataset: Path, output_dir: Path, window_seconds: float) -> dict[str, Any]:
    events, metrics = load_dataset(dataset)
    correlations = correlate_events(events, window_seconds=window_seconds)
    alert_path = _write_alerts(correlations, output_dir=output_dir)
    png_path, html_path = render_timeline(
        metrics=metrics,
        events=events,
        correlations=correlations,
        output_dir=output_dir,
    )
    return {
        "alerts": alert_path,
        "timeline_png": png_path,
        "timeline_html": html_path,
        "correlations": correlations,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "dataset",
        type=Path,
        help="Path to a JSON dataset emitted by heuristic modules.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("correlation_output"),
        help="Directory to store JSON alerts and timeline assets.",
    )
    parser.add_argument(
        "--window",
        type=float,
        default=5.0,
        help="Window size (seconds) after a trigger to include collapse/pump signals.",
    )

    args = parser.parse_args(argv)
    result = run(
        dataset=args.dataset, output_dir=args.output_dir, window_seconds=args.window
    )
    print(
        json.dumps(
            {
                "alerts": str(result["alerts"]),
                "timeline_png": str(result["timeline_png"]),
                "timeline_html": str(result["timeline_html"]),
                "correlation_count": len(result["correlations"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
