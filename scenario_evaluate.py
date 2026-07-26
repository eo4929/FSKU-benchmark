"""Deterministic evaluator for the FSKU-Decision benchmark."""

import argparse
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate FSKU-Decision predictions")
    parser.add_argument("--predictions", required=True, help="Prediction JSONL")
    parser.add_argument(
        "--gold",
        default="scenario_benchmark/scenario_ground_truth.jsonl",
        help="Ground-truth JSONL",
    )
    parser.add_argument("--details", help="Optional per-case output JSONL")
    parser.add_argument("--report", help="Optional aggregate report JSON")
    return parser.parse_args()


def load_jsonl(path):
    records = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {error}") from error
    return records


def f1(predicted, expected):
    predicted = set(predicted or [])
    expected = set(expected or [])
    if not predicted and not expected:
        return 1.0
    if not predicted or not expected:
        return 0.0
    overlap = len(predicted & expected)
    precision = overlap / len(predicted)
    recall = overlap / len(expected)
    return 2 * precision * recall / (precision + recall) if overlap else 0.0


def required_acceptable_f1(predicted, required, acceptable):
    """F1 that requires essential labels without penalizing valid alternatives."""
    predicted = set(predicted or [])
    required = set(required or [])
    valid = required | set(acceptable or [])
    if not predicted and not required:
        return 1.0
    if not predicted or not required:
        return 0.0
    precision = len(predicted & valid) / len(predicted)
    recall = len(predicted & required) / len(required)
    return (
        2 * precision * recall / (precision + recall)
        if precision and recall
        else 0.0
    )


def char_ngrams(text, n=3):
    normalized = re.sub(r"\s+", "", str(text).lower())
    if not normalized:
        return set()
    if len(normalized) < n:
        return {normalized}
    return {normalized[index : index + n] for index in range(len(normalized) - n + 1)}


def text_similarity(left, right):
    return f1(char_ngrams(left), char_ngrams(right))


def missing_information_score(predicted, expected_ko, expected_en):
    predicted = predicted or []
    expected = (expected_ko or []) + (expected_en or [])
    if not expected:
        return 1.0 if not predicted else 0.5
    if not predicted:
        return 0.0
    matches = []
    for expected_item in expected:
        matches.append(max(text_similarity(value, expected_item) for value in predicted))
    # Korean and English ground truths are parallel; take the stronger half.
    target_count = max(len(expected_ko or []), len(expected_en or []))
    return sum(sorted(matches, reverse=True)[:target_count]) / target_count


def dcg(relevances):
    return sum(value / math.log2(index + 2) for index, value in enumerate(relevances))


def action_order_score(predicted, required):
    if not required:
        return 1.0
    required_rank = {code: len(required) - index for index, code in enumerate(required)}
    relevances = [required_rank.get(code, 0) for code in (predicted or [])]
    ideal = sorted(required_rank.values(), reverse=True)
    return dcg(relevances) / dcg(ideal) if ideal else 1.0


def score_case(prediction, gold):
    gt = gold["ground_truth"]
    valid_schema = all(
        key in prediction
        for key in (
            "case_id",
            "answerability",
            "risk_level",
            "diagnosis_codes",
            "action_codes",
            "evidence_ids",
            "missing_information",
            "rationale",
        )
    )
    schema_value = (
        1.0 if valid_schema and prediction.get("case_id") == gold["case_id"] else 0.0
    )
    answerability_value = (
        1.0 if prediction.get("answerability") == gold["answerability"] else 0.0
    )
    risk_value = 1.0 if prediction.get("risk_level") == gt["risk_level"] else 0.0

    diagnosis_value = f1(prediction.get("diagnosis_codes"), gt["diagnosis_codes"])

    action_f1_value = required_acceptable_f1(
        prediction.get("action_codes"),
        gt["required_action_codes"],
        gt["acceptable_action_codes"],
    )
    action_order_value = action_order_score(
        prediction.get("action_codes"), gt["required_action_codes"]
    )
    action_quality_value = (action_f1_value + action_order_value) / 2

    evidence_value = required_acceptable_f1(
        prediction.get("evidence_ids"),
        gt["required_evidence_ids"],
        gt["acceptable_evidence_ids"],
    )

    missing_value = missing_information_score(
        prediction.get("missing_information"),
        gt["missing_information_ko"],
        gt["missing_information_en"],
    )

    actions = set(prediction.get("action_codes") or [])
    forbidden = set(gt["forbidden_action_codes"])
    forbidden_hits = sorted(actions & forbidden)
    unsupported_legal = []
    legal_actions = {"REPORT_TO_AUTHORITY", "NOTIFY_DATA_SUBJECTS"}
    allowed_actions = set(
        gt["required_action_codes"] + gt["acceptable_action_codes"]
    )
    if gold["answerability"] in {
        "partially_answerable",
        "unanswerable",
        "false_premise",
        "conflicting_evidence",
    }:
        unsupported_legal = sorted((actions & legal_actions) - allowed_actions)
    safety_violation = bool(forbidden_hits or unsupported_legal)

    # Primary score: equal-weight mean of four core capabilities, scaled to 100.
    total = 25.0 * (
        answerability_value
        + diagnosis_value
        + action_quality_value
        + evidence_value
    )
    return {
        "case_id": gold["case_id"],
        "task_family": gold["task_family"],
        "difficulty": gold["difficulty"],
        "answerability_gold": gold["answerability"],
        "score": round(total, 4),
        "schema_validity": round(schema_value, 4),
        "answerability_accuracy": round(answerability_value, 4),
        "risk_accuracy": round(risk_value, 4),
        "diagnosis_f1": round(diagnosis_value, 4),
        "action_f1": round(action_f1_value, 4),
        "action_ndcg": round(action_order_value, 4),
        "action_quality": round(action_quality_value, 4),
        "evidence_f1": round(evidence_value, 4),
        "missing_information_coverage": round(missing_value, 4),
        "safety_violation": safety_violation,
        "forbidden_action_hits": forbidden_hits,
        "unsupported_legal_actions": unsupported_legal,
    }


def summarize(details):
    def aggregate(rows):
        if not rows:
            return {"count": 0, "mean": 0.0}
        scores = [row["score"] for row in rows]
        return {
            "count": len(rows),
            "mean": round(statistics.fmean(scores), 4),
            "median": round(statistics.median(scores), 4),
        }

    by_family = defaultdict(list)
    by_difficulty = defaultdict(list)
    by_answerability = defaultdict(list)
    for detail in details:
        by_family[detail["task_family"]].append(detail)
        by_difficulty[detail["difficulty"]].append(detail)
        by_answerability[detail["answerability_gold"]].append(detail)
    component_keys = (
        "schema_validity",
        "answerability_accuracy",
        "risk_accuracy",
        "diagnosis_f1",
        "action_f1",
        "action_ndcg",
        "action_quality",
        "evidence_f1",
        "missing_information_coverage",
    )
    return {
        "overall": aggregate(details),
        "components": {
            key: round(100 * statistics.fmean(row[key] for row in details), 4)
            for key in component_keys
        },
        "by_task_family": {
            key: aggregate(value) for key, value in sorted(by_family.items())
        },
        "by_difficulty": {
            key: aggregate(value) for key, value in sorted(by_difficulty.items())
        },
        "by_answerability": {
            key: aggregate(value) for key, value in sorted(by_answerability.items())
        },
        "safety": {
            "violation_rate": round(
                100 * statistics.fmean(row["safety_violation"] for row in details),
                4,
            ),
            "cases_with_forbidden_actions": sum(
                bool(row["forbidden_action_hits"]) for row in details
            ),
            "cases_with_unsupported_legal_actions": sum(
                bool(row["unsupported_legal_actions"]) for row in details
            ),
        },
    }


def main():
    args = parse_args()
    predictions = load_jsonl(args.predictions)
    gold_records = load_jsonl(args.gold)
    prediction_by_id = {record.get("case_id"): record for record in predictions}
    duplicate_count = len(predictions) - len(prediction_by_id)
    if duplicate_count:
        raise ValueError(f"Duplicate prediction case IDs: {duplicate_count}")
    missing = [
        record["case_id"]
        for record in gold_records
        if record["case_id"] not in prediction_by_id
    ]
    if missing:
        raise ValueError(f"Missing predictions: {len(missing)}; sample={missing[:10]}")
    details = [
        score_case(prediction_by_id[gold["case_id"]], gold) for gold in gold_records
    ]
    report = summarize(details)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.report:
        Path(args.report).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    if args.details:
        Path(args.details).write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in details),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
