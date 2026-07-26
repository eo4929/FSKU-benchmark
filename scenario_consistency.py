"""Measure Korean-English decision consistency for paired predictions."""

import argparse
import json
import statistics
from pathlib import Path

from scenario_evaluate import f1, load_jsonl


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kor", required=True, help="Korean prediction JSONL")
    parser.add_argument("--eng", required=True, help="English prediction JSONL")
    parser.add_argument("--report", help="Optional aggregate report JSON")
    args = parser.parse_args()
    kor = {row["case_id"]: row for row in load_jsonl(args.kor)}
    eng = {row["case_id"]: row for row in load_jsonl(args.eng)}
    if set(kor) != set(eng):
        raise ValueError("Korean and English prediction case IDs differ")
    details = []
    for case_id in sorted(kor):
        left, right = kor[case_id], eng[case_id]
        values = {
            "answerability": float(
                left.get("answerability") == right.get("answerability")
            ),
            "risk": float(left.get("risk_level") == right.get("risk_level")),
            "diagnosis": f1(
                left.get("diagnosis_codes"), right.get("diagnosis_codes")
            ),
            "actions": f1(left.get("action_codes"), right.get("action_codes")),
            "evidence": f1(left.get("evidence_ids"), right.get("evidence_ids")),
        }
        values["overall"] = statistics.fmean(values.values())
        details.append({"case_id": case_id, **values})
    report = {
        "case_count": len(details),
        "cross_lingual_consistency": round(
            100 * statistics.fmean(row["overall"] for row in details), 4
        ),
        "components": {
            key: round(100 * statistics.fmean(row[key] for row in details), 4)
            for key in ("answerability", "risk", "diagnosis", "actions", "evidence")
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.report:
        Path(args.report).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
