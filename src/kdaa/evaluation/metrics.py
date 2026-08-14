"""Evaluation metrics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SetMetrics:
    precision: float
    recall: float
    f1: float
    true_positive: int
    false_positive: int
    false_negative: int


def set_metrics(predicted: set[str], truth: set[str]) -> SetMetrics:
    tp = len(predicted & truth)
    fp = len(predicted - truth)
    fn = len(truth - predicted)
    precision = tp / (tp + fp) if tp + fp else 1.0 if not truth else 0.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return SetMetrics(precision, recall, f1, tp, fp, fn)
