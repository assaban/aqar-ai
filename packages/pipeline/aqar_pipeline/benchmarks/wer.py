"""
Aqar.ai: Word Error Rate (WER) Calculator
===========================================
Measures transcription accuracy by comparing Whisper output
against manually transcribed reference text.

WER = (Substitutions + Insertions + Deletions) / Reference Words

Lower WER is better. Typical values:
  - 0.05-0.15: Good (clean English/Arabic)
  - 0.15-0.30: Acceptable (Darija/noisy audio)
  - 0.30+: Poor (heavy dialect, background noise)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass


@dataclass
class WERResult:
    """Result of a WER calculation."""

    wer: float
    substitutions: int
    insertions: int
    deletions: int
    ref_word_count: int
    hyp_word_count: int
    reference_id: str = ""


def _tokenize(text: str) -> list[str]:
    """Simple word tokenization: lowercase, split on whitespace."""
    return text.strip().lower().split()


def _edit_distance(ref: list[str], hyp: list[str]) -> tuple[int, int, int]:
    """
    Calculate the minimum edit distance between reference and hypothesis.
    Returns (substitutions, insertions, deletions).
    """
    n = len(ref)
    m = len(hyp)

    # DP table: dp[i][j] = (cost, subs, ins, dels)
    dp = [[(0, 0, 0, 0) for _ in range(m + 1)] for _ in range(n + 1)]

    for i in range(1, n + 1):
        dp[i][0] = (i, 0, 0, i)
    for j in range(1, m + 1):
        dp[0][j] = (j, 0, j, 0)

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref[i - 1] == hyp[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                # Substitution
                sub = dp[i - 1][j - 1]
                sub_cost = (sub[0] + 1, sub[1] + 1, sub[2], sub[3])

                # Deletion (word in ref but not in hyp)
                dele = dp[i - 1][j]
                del_cost = (dele[0] + 1, dele[1], dele[2], dele[3] + 1)

                # Insertion (word in hyp but not in ref)
                ins = dp[i][j - 1]
                ins_cost = (ins[0] + 1, ins[1], ins[2] + 1, ins[3])

                dp[i][j] = min(sub_cost, del_cost, ins_cost, key=lambda x: x[0])

    final = dp[n][m]
    return final[1], final[2], final[3]


def calculate_wer(reference: str, hypothesis: str, reference_id: str = "") -> WERResult:
    """
    Calculate Word Error Rate between reference and hypothesis text.

    Args:
        reference: Ground truth (manually transcribed) text.
        hypothesis: System output (Whisper transcription) text.
        reference_id: Identifier for this test case.

    Returns:
        WERResult with WER score and error breakdown.
    """
    ref_words = _tokenize(reference)
    hyp_words = _tokenize(hypothesis)

    if not ref_words:
        return WERResult(
            wer=0.0 if not hyp_words else 1.0,
            substitutions=0,
            insertions=len(hyp_words),
            deletions=0,
            ref_word_count=0,
            hyp_word_count=len(hyp_words),
            reference_id=reference_id,
        )

    subs, ins, dels = _edit_distance(ref_words, hyp_words)
    wer = (subs + ins + dels) / len(ref_words)

    return WERResult(
        wer=round(wer, 4),
        substitutions=subs,
        insertions=ins,
        deletions=dels,
        ref_word_count=len(ref_words),
        hyp_word_count=len(hyp_words),
        reference_id=reference_id,
    )


def run_wer_benchmark(golden_dir: str) -> dict:
    """
    Run WER benchmark against all golden test cases in a directory.

    Expected directory structure:
      golden_dir/
        case_001.json  # {"id": "...", "reference": "...", "hypothesis": "..."}
        case_002.json

    Returns:
        Dict with per-case results and aggregate statistics.
    """
    results = []

    if not os.path.isdir(golden_dir):
        return {"error": f"Directory not found: {golden_dir}", "results": []}

    for filename in sorted(os.listdir(golden_dir)):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(golden_dir, filename)
        with open(filepath) as f:
            case = json.load(f)

        ref = case.get("reference", "")
        hyp = case.get("hypothesis", "")
        case_id = case.get("id", filename)

        result = calculate_wer(ref, hyp, reference_id=case_id)
        results.append(result)

    if not results:
        return {"error": "No test cases found", "results": []}

    avg_wer = sum(r.wer for r in results) / len(results)
    min_wer = min(r.wer for r in results)
    max_wer = max(r.wer for r in results)

    return {
        "total_cases": len(results),
        "avg_wer": round(avg_wer, 4),
        "min_wer": round(min_wer, 4),
        "max_wer": round(max_wer, 4),
        "results": [
            {
                "id": r.reference_id,
                "wer": r.wer,
                "substitutions": r.substitutions,
                "insertions": r.insertions,
                "deletions": r.deletions,
                "ref_words": r.ref_word_count,
            }
            for r in results
        ],
    }
