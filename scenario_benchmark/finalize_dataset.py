"""Apply benchmark-wide safety invariants and regenerate public exports."""

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INCIDENT_FAMILIES = {
    "incident_triage",
    "account_takeover",
    "ransomware_resilience",
    "privacy_breach",
    "third_party_supply_chain",
}
NEVER_FORBID = {
    "PRESERVE_EVIDENCE",
    "PRESERVE_AND_REVIEW_ACCESS_LOGS",
    "REQUEST_ADDITIONAL_INFORMATION",
    "ESCALATE_TO_MANAGEMENT",
}


def load_jsonl(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path, records):
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )


def add_unique(values, code):
    if code not in values:
        values.append(code)


def remove_from_all(gt, code):
    for field in (
        "required_action_codes",
        "acceptable_action_codes",
        "forbidden_action_codes",
    ):
        gt[field] = [value for value in gt[field] if value != code]


def normalize(case):
    gt = case["ground_truth"]
    gt["forbidden_action_codes"] = [
        code for code in gt["forbidden_action_codes"] if code not in NEVER_FORBID
    ]
    if case["answerability"] != "answerable":
        remove_from_all(gt, "REQUEST_ADDITIONAL_INFORMATION")
        add_unique(gt["required_action_codes"], "REQUEST_ADDITIONAL_INFORMATION")
        if not gt["missing_information_ko"]:
            gt["missing_information_ko"] = ["확정적 판단에 필요한 추가 사실관계"]
        if not gt["missing_information_en"]:
            gt["missing_information_en"] = [
                "Additional case facts required for a definitive determination"
            ]
    if case["task_family"] in INCIDENT_FAMILIES:
        remove_from_all(gt, "PRESERVE_EVIDENCE")
        if case["answerability"] == "false_premise":
            add_unique(gt["acceptable_action_codes"], "PRESERVE_EVIDENCE")
        else:
            gt["required_action_codes"].insert(0, "PRESERVE_EVIDENCE")
    if gt["risk_level"] in {"high", "critical"}:
        if "ESCALATE_TO_MANAGEMENT" not in (
            gt["required_action_codes"] + gt["acceptable_action_codes"]
        ):
            gt["acceptable_action_codes"].append("ESCALATE_TO_MANAGEMENT")
    required = set(gt["required_action_codes"])
    gt["acceptable_action_codes"] = [
        code for code in dict.fromkeys(gt["acceptable_action_codes"]) if code not in required
    ]
    allowed = required | set(gt["acceptable_action_codes"])
    gt["forbidden_action_codes"] = [
        code for code in dict.fromkeys(gt["forbidden_action_codes"]) if code not in allowed
    ]
    case["difficulty"] = (
        "expert"
        if (
            case["answerability"]
            in {"unanswerable", "false_premise", "conflicting_evidence"}
            or case["reasoning_hops"] >= 4
            or (
                case["answerability"] == "partially_answerable"
                and case["reasoning_hops"] >= 3
            )
        )
        else "hard"
    )
    tags = [
        case["task_family"],
        "evidence_grounding",
        "multi_hop_reasoning",
        "cross_lingual_consistency",
    ]
    if case["answerability"] != "answerable":
        tags.extend(["uncertainty_calibration", "safe_abstention"])
    if case["answerability"] == "conflicting_evidence":
        tags.append("conflict_resolution")
    if case["answerability"] == "false_premise":
        tags.append("false_premise_detection")
    if any(item["source_id"] for item in case["evidence"]):
        tags.append("regulatory_or_standard_reasoning")
    if any(
        item["evidence_type"]
        in {
            "system_log",
            "api_log",
            "access_log",
            "transaction_summary",
            "configuration",
            "network_log",
        }
        for item in case["evidence"]
    ):
        tags.append("technical_artifact_analysis")
    case["capability_tags"] = list(dict.fromkeys(tags))
    return case


def public_record(case, language):
    suffix = "ko" if language == "kor" else "en"
    return {
        "case_id": case["case_id"],
        "split": case["split"],
        "task_family": case["task_family"],
        "difficulty": case["difficulty"],
        "as_of": case["as_of"],
        "role": case[f"role_{suffix}"],
        "scenario": case[f"scenario_{suffix}"],
        "question": case[f"question_{suffix}"],
        "evidence": [
            {
                "evidence_id": item["evidence_id"],
                "evidence_type": item["evidence_type"],
                "content": item[f"content_{suffix}"],
                "source_id": item["source_id"],
            }
            for item in case["evidence"]
        ],
    }


def gold_record(case):
    return {
        "case_id": case["case_id"],
        "split": case["split"],
        "task_family": case["task_family"],
        "difficulty": case["difficulty"],
        "answerability": case["answerability"],
        "reasoning_hops": case["reasoning_hops"],
        "capability_tags": case["capability_tags"],
        "ground_truth": case["ground_truth"],
    }


def main():
    master_path = ROOT / "scenario_master.jsonl"
    cases = [normalize(case) for case in load_jsonl(master_path)]
    kor = ROOT / "scenario_test(kor).jsonl"
    eng = ROOT / "scenario_test(eng).jsonl"
    gold = ROOT / "scenario_ground_truth.jsonl"
    write_jsonl(master_path, cases)
    write_jsonl(kor, [public_record(case, "kor") for case in cases])
    write_jsonl(eng, [public_record(case, "eng") for case in cases])
    write_jsonl(gold, [gold_record(case) for case in cases])
    paths = [master_path, kor, eng, gold]
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    manifest["sha256"] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths
    }
    manifest["postprocessing"] = [
        "safe evidence-preservation invariant",
        "required information request for non-answerable cases",
        "management escalation not forbidden for high/critical cases",
        "allowed/forbidden action disjointness",
        "difficulty calibration from reasoning hops and answerability structure",
        "controlled capability-tag normalization",
    ]
    manifest["distributions"] = {
        field: dict(Counter(case[field] for case in cases))
        for field in ("split", "task_family", "difficulty", "answerability")
    }
    eng_report = ROOT / "baseline_gpt-4.1-mini(eng)_report.json"
    kor_report = ROOT / "baseline_gpt-4.1-mini(kor)_report.json"
    consistency_report = ROOT / "baseline_gpt-4.1-mini_consistency_report.json"
    if eng_report.exists() and kor_report.exists() and consistency_report.exists():
        eng_result = json.loads(eng_report.read_text(encoding="utf-8"))
        kor_result = json.loads(kor_report.read_text(encoding="utf-8"))
        consistency = json.loads(consistency_report.read_text(encoding="utf-8"))
        manifest["pilot_baseline"] = {
            "model": "gpt-4.1-mini",
            "temperature": 0,
            "english_score": eng_result["overall"]["mean"],
            "korean_score": kor_result["overall"]["mean"],
            "english_hard_score": eng_result["by_difficulty"]["hard"]["mean"],
            "english_expert_score": eng_result["by_difficulty"]["expert"]["mean"],
            "korean_hard_score": kor_result["by_difficulty"]["hard"]["mean"],
            "korean_expert_score": kor_result["by_difficulty"]["expert"]["mean"],
            "cross_lingual_consistency": consistency[
                "cross_lingual_consistency"
            ],
        }
    (ROOT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "cases": len(cases),
                "answerability": Counter(case["answerability"] for case in cases),
                "status": "finalized",
            },
            ensure_ascii=False,
            default=dict,
        )
    )


if __name__ == "__main__":
    main()
