"""
Aqar.ai: Extraction Accuracy Scorer
=====================================
Measures LLM extraction accuracy by comparing extracted fields
against manually annotated ground truth.

Calculates per-field accuracy and overall F1 score.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


@dataclass
class FieldScore:
    """Accuracy score for a single extracted field."""

    field_name: str
    correct: int = 0
    incorrect: int = 0
    missing: int = 0

    @property
    def accuracy(self) -> float:
        total = self.correct + self.incorrect + self.missing
        return round(self.correct / total, 4) if total > 0 else 0.0


@dataclass
class ExtractionScore:
    """Overall extraction accuracy for a test case."""

    case_id: str
    field_scores: dict[str, FieldScore] = field(default_factory=dict)

    @property
    def overall_accuracy(self) -> float:
        if not self.field_scores:
            return 0.0
        accuracies = [fs.accuracy for fs in self.field_scores.values()]
        return round(sum(accuracies) / len(accuracies), 4)


# Fields to evaluate (must match the Property model)
SCORED_FIELDS = [
    "property_type",
    "listing_type",
    "price",
    "area_sqm",
    "rooms",
    "bedrooms",
    "bathrooms",
    "legal_status",
    "neighborhood",
]

# Numeric fields that allow tolerance
NUMERIC_FIELDS = {"price": 0.05, "area_sqm": 0.10}  # 5% tolerance, 10% tolerance


def _values_match(field_name: str, expected, actual) -> bool:
    """Compare expected vs actual values with type-appropriate logic."""
    if expected is None and actual is None:
        return True
    if expected is None or actual is None:
        return False

    # Numeric comparison with tolerance
    if field_name in NUMERIC_FIELDS:
        try:
            exp_num = float(expected)
            act_num = float(actual)
            if exp_num == 0:
                return act_num == 0
            tolerance = NUMERIC_FIELDS[field_name]
            return abs(exp_num - act_num) / exp_num <= tolerance
        except (ValueError, TypeError):
            return False

    # String comparison (case-insensitive, stripped)
    return str(expected).strip().lower() == str(actual).strip().lower()


def score_extraction(
    expected: dict,
    actual: dict,
    case_id: str = "",
) -> ExtractionScore:
    """
    Score a single extraction against ground truth.

    Args:
        expected: Ground truth property data.
        actual: LLM-extracted property data.
        case_id: Identifier for this test case.

    Returns:
        ExtractionScore with per-field accuracy.
    """
    score = ExtractionScore(case_id=case_id)

    for field_name in SCORED_FIELDS:
        fs = FieldScore(field_name=field_name)
        exp_val = expected.get(field_name)
        act_val = actual.get(field_name)

        if exp_val is None:
            # Field not in ground truth, skip
            continue
        elif act_val is None:
            fs.missing = 1
        elif _values_match(field_name, exp_val, act_val):
            fs.correct = 1
        else:
            fs.incorrect = 1

        score.field_scores[field_name] = fs

    return score


def run_extraction_benchmark(golden_dir: str) -> dict:
    """
    Run extraction benchmark against all golden test cases.

    Expected directory structure:
      golden_dir/
        case_001.json  # {"id": "...", "expected": {...}, "actual": {...}}

    Returns:
        Dict with per-case results, per-field aggregates, and overall accuracy.
    """
    scores = []

    if not os.path.isdir(golden_dir):
        return {"error": f"Directory not found: {golden_dir}", "results": []}

    for filename in sorted(os.listdir(golden_dir)):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(golden_dir, filename)
        with open(filepath) as f:
            case = json.load(f)

        case_id = case.get("id", filename)
        expected = case.get("expected", {})
        actual = case.get("actual", {})

        score = score_extraction(expected, actual, case_id=case_id)
        scores.append(score)

    if not scores:
        return {"error": "No test cases found", "results": []}

    # Aggregate per-field stats
    field_aggregates = {}
    for field_name in SCORED_FIELDS:
        total_correct = sum(
            s.field_scores[field_name].correct for s in scores if field_name in s.field_scores
        )
        total_incorrect = sum(
            s.field_scores[field_name].incorrect for s in scores if field_name in s.field_scores
        )
        total_missing = sum(
            s.field_scores[field_name].missing for s in scores if field_name in s.field_scores
        )
        total = total_correct + total_incorrect + total_missing
        field_aggregates[field_name] = {
            "accuracy": round(total_correct / total, 4) if total > 0 else 0.0,
            "correct": total_correct,
            "incorrect": total_incorrect,
            "missing": total_missing,
        }

    avg_accuracy = sum(s.overall_accuracy for s in scores) / len(scores)

    return {
        "total_cases": len(scores),
        "avg_accuracy": round(avg_accuracy, 4),
        "field_accuracies": field_aggregates,
        "results": [
            {
                "id": s.case_id,
                "overall_accuracy": s.overall_accuracy,
                "fields": {
                    k: {
                        "accuracy": v.accuracy,
                        "correct": v.correct,
                        "incorrect": v.incorrect,
                        "missing": v.missing,
                    }
                    for k, v in s.field_scores.items()
                },
            }
            for s in scores
        ],
    }
