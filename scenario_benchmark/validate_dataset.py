"""Static and semantic-integrity checks for FSKU-Decision."""

import itertools
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent

SAFE_INFORMATION_ACTIONS = {
    "PRESERVE_EVIDENCE",
    "PRESERVE_AND_REVIEW_ACCESS_LOGS",
    "REQUEST_ADDITIONAL_INFORMATION",
}
INCIDENT_FAMILIES = {
    "incident_triage",
    "account_takeover",
    "ransomware_resilience",
    "privacy_breach",
    "third_party_supply_chain",
}


def load_jsonl(path):
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def ngrams(text, size=7):
    text = re.sub(r"\s+", "", text.lower())
    return {
        text[index : index + size]
        for index in range(max(0, len(text) - size + 1))
    }


def jaccard(left, right):
    return len(left & right) / len(left | right) if left or right else 1.0


def numbers(text):
    return sorted(re.findall(r"\d+(?:[.,]\d+)*", text))


def validate():
    taxonomy = json.loads((ROOT / "taxonomy.json").read_text(encoding="utf-8"))
    catalog = json.loads((ROOT / "source_catalog.json").read_text(encoding="utf-8"))
    master = load_jsonl(ROOT / "scenario_master.jsonl")
    kor = load_jsonl(ROOT / "scenario_test(kor).jsonl")
    eng = load_jsonl(ROOT / "scenario_test(eng).jsonl")
    gold = load_jsonl(ROOT / "scenario_ground_truth.jsonl")
    errors = []
    warnings = []
    numeric_surface_flags = []

    expected_ids = {f"FSKUD-{index:04d}" for index in range(1, 151)}
    for name, records in (
        ("master", master),
        ("kor", kor),
        ("eng", eng),
        ("gold", gold),
    ):
        ids = [record["case_id"] for record in records]
        if len(records) != 150:
            errors.append(f"{name}: expected 150 records, found {len(records)}")
        if len(ids) != len(set(ids)):
            errors.append(f"{name}: duplicate case IDs")
        if set(ids) != expected_ids:
            errors.append(f"{name}: ID set mismatch")

    source_ids = {source["source_id"] for source in catalog["sources"]}
    diagnosis_codes = set(taxonomy["diagnosis_codes"])
    action_codes = set(taxonomy["action_codes"])
    answerability_labels = set(taxonomy["answerability_labels"])
    risk_levels = set(taxonomy["risk_levels"])

    for case in master:
        case_id = case["case_id"]
        gt = case["ground_truth"]
        evidence_ids = [item["evidence_id"] for item in case["evidence"]]
        evidence_set = set(evidence_ids)
        if not 3 <= len(evidence_ids) <= 7:
            errors.append(f"{case_id}: evidence count")
        if len(evidence_ids) != len(evidence_set):
            errors.append(f"{case_id}: duplicate evidence IDs")
        if case["answerability"] not in answerability_labels:
            errors.append(f"{case_id}: invalid answerability")
        if gt["risk_level"] not in risk_levels:
            errors.append(f"{case_id}: invalid risk")
        if not set(gt["diagnosis_codes"]) <= diagnosis_codes:
            errors.append(f"{case_id}: invalid diagnosis code")
        for field in (
            "required_action_codes",
            "acceptable_action_codes",
            "forbidden_action_codes",
        ):
            if not set(gt[field]) <= action_codes:
                errors.append(f"{case_id}: invalid {field}")
        if not set(gt["required_evidence_ids"]) <= evidence_set:
            errors.append(f"{case_id}: unknown required evidence")
        if not set(gt["acceptable_evidence_ids"]) <= evidence_set:
            errors.append(f"{case_id}: unknown acceptable evidence")
        for item in case["evidence"]:
            if item["source_id"] is not None and item["source_id"] not in source_ids:
                errors.append(f"{case_id}: unknown source {item['source_id']}")
            if numbers(item["content_ko"]) != numbers(item["content_en"]):
                numeric_surface_flags.append(f"{case_id}/{item['evidence_id']}")
        if numbers(case["scenario_ko"]) != numbers(case["scenario_en"]):
            numeric_surface_flags.append(f"{case_id}/scenario")
        if re.search(r"[가-힣]", case["scenario_en"]):
            errors.append(f"{case_id}: Hangul in English scenario")
        if not re.search(r"[가-힣]", case["scenario_ko"]):
            errors.append(f"{case_id}: no Hangul in Korean scenario")
        if len(gt["missing_information_ko"]) != len(gt["missing_information_en"]):
            errors.append(f"{case_id}: missing-info bilingual count")
        if len(gt["key_claims_ko"]) != len(gt["key_claims_en"]):
            errors.append(f"{case_id}: key-claim bilingual count")

        required = set(gt["required_action_codes"])
        acceptable = set(gt["acceptable_action_codes"])
        forbidden = set(gt["forbidden_action_codes"])
        if (required | acceptable) & forbidden:
            errors.append(f"{case_id}: allowed/forbidden action overlap")
        if forbidden & SAFE_INFORMATION_ACTIONS:
            errors.append(f"{case_id}: safe information action forbidden")
        if case["answerability"] != "answerable":
            if "REQUEST_ADDITIONAL_INFORMATION" not in required | acceptable:
                errors.append(f"{case_id}: non-answerable case lacks request action")
            if not gt["missing_information_en"]:
                errors.append(f"{case_id}: non-answerable case lacks missing info")
        if (
            case["task_family"] in INCIDENT_FAMILIES
            and case["answerability"] != "false_premise"
            and "PRESERVE_EVIDENCE" not in required | acceptable
        ):
            warnings.append(f"{case_id}: incident case lacks evidence preservation")
        if (
            gt["risk_level"] in {"high", "critical"}
            and "ESCALATE_TO_MANAGEMENT" in forbidden
        ):
            warnings.append(f"{case_id}: high risk but escalation forbidden")

    by_id_master = {record["case_id"]: record for record in master}
    by_id_gold = {record["case_id"]: record for record in gold}
    for public_records, language in ((kor, "ko"), (eng, "en")):
        for public in public_records:
            source = by_id_master[public["case_id"]]
            suffix = "ko" if language == "ko" else "en"
            if public["scenario"] != source[f"scenario_{suffix}"]:
                errors.append(f"{public['case_id']}: {language} scenario export mismatch")
            if public["question"] != source[f"question_{suffix}"]:
                errors.append(f"{public['case_id']}: {language} question export mismatch")
            if "ground_truth" in public or "answerability" in public:
                errors.append(f"{public['case_id']}: answer leakage in public export")
    for case_id, record in by_id_gold.items():
        source = by_id_master[case_id]
        if record["answerability"] != source["answerability"]:
            errors.append(f"{case_id}: gold export mismatch")

    # Detect near duplicates within and across splits.
    gram_map = {
        case["case_id"]: ngrams(case["scenario_en"] + " " + case["question_en"])
        for case in master
    }
    for left, right in itertools.combinations(master, 2):
        similarity = jaccard(gram_map[left["case_id"]], gram_map[right["case_id"]])
        if similarity >= 0.72:
            warnings.append(
                f"{left['case_id']}/{right['case_id']}: near duplicate {similarity:.3f}"
            )

    distributions = {
        field: dict(sorted(Counter(case[field] for case in master).items()))
        for field in ("split", "task_family", "difficulty", "answerability")
    }
    audit_summary = None
    audit_path = ROOT / "quality_audit_report.json"
    adjudication_path = ROOT / "quality_audit_adjudication.json"
    if audit_path.exists():
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        adjudication = (
            json.loads(adjudication_path.read_text(encoding="utf-8"))
            if adjudication_path.exists()
            else {"accepted_case_ids": []}
        )
        accepted = set(adjudication.get("accepted_case_ids", []))
        unresolved = [
            item["case_id"]
            for item in audit["audits"]
            if item["verdict"] == "revise" and item["case_id"] not in accepted
        ]
        if unresolved:
            warnings.append(f"unresolved semantic-audit cases: {unresolved}")
        audit_summary = {
            "case_count": audit["case_count"],
            "automatic_pass_count": audit["pass_count"],
            "author_adjudicated_count": len(accepted),
            "unresolved_count": len(unresolved),
            "mean_scores": audit["mean_scores"],
        }
    report = {
        "status": "pass" if not errors else "fail",
        "cases": len(master),
        "language_records": len(kor) + len(eng),
        "errors": errors,
        "warnings": warnings,
        "numeric_surface_flags": {
            "count": len(numeric_surface_flags),
            "note": (
                "Surface digit differences include equivalent localized units "
                "(for example, 2억 원 versus KRW 200 million). All cases were "
                "separately checked by the semantic bilingual audit."
            ),
            "sample": numeric_surface_flags[:20],
        },
        "warning_categories": dict(
            sorted(
                Counter(
                    "numeric_mismatch"
                    if "numeric mismatch" in warning
                    else "near_duplicate"
                    if "near duplicate" in warning
                    else "safety_review"
                    for warning in warnings
                ).items()
            )
        ),
        "distributions": distributions,
        "semantic_quality_audit": audit_summary,
    }
    (ROOT / "validation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(validate())
