"""Simulate auto rollback by creating a PR."""

from __future__ import annotations


def check_and_rollback(error_rate: float) -> str:
    if error_rate > 0.02:
        return "ROLLBACK"
    return "OK"


__all__ = ["check_and_rollback"]
