"""Generate FSKU-Decision cases with a two-pass author/reviewer workflow.

This script is retained for reproducibility. It never reads the legacy FSKU
question files. It sends only the public source catalog, taxonomy, and generated
synthetic cases to the configured OpenAI API model.
"""

import concurrent.futures
import hashlib
import json
import os
import random
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATALOG = json.loads((ROOT / "source_catalog.json").read_text(encoding="utf-8"))
TAXONOMY = json.loads((ROOT / "taxonomy.json").read_text(encoding="utf-8"))
CACHE = ROOT / ".generation_cache"
CACHE.mkdir(exist_ok=True)

MODEL = os.environ.get("FSKU_DECISION_MODEL", "gpt-4.1-mini")
WORKERS = int(os.environ.get("FSKU_DECISION_WORKERS", "1"))
CASES_PER_BATCH = 5
SEED = 20260724

FAMILY_SOURCES = {
    "incident_triage": ["KR-EFSR", "KR-KISA-ISMS-IR", "NIST-SP800-171R3-IR"],
    "account_takeover": ["KR-EFTA-21", "KR-KISA-ISMS-IR", "NIST-SP800-171R3-IR"],
    "ransomware_resilience": [
        "KR-FSC-RANSOMWARE-2025",
        "KR-KISA-ISMS-IR",
        "NIST-SP800-171R3-IR",
    ],
    "privacy_breach": ["KR-PIPA-16", "KR-PIPA-29", "KR-PIPA-34", "KR-KISA-ISMS-IR"],
    "api_authorization": ["KR-PIPA-29", "OWASP-API1-2023", "OWASP-API3-2023"],
    "third_party_supply_chain": [
        "KR-EFSR",
        "KR-PIPA-29",
        "OWASP-API10-2023",
        "NIST-SP800-171R3-IR",
    ],
    "cloud_zero_trust": ["KR-EFTA-21", "KR-FSI-ZT-2026", "NIST-SP800-207-ZT"],
    "ai_security_governance": [
        "KR-PIPA-16",
        "KR-PIPA-29",
        "KR-FSC-AI-2026",
        "KR-FSI-TRENDS-2026",
    ],
    "vulnerability_governance": [
        "KR-EFTA-21",
        "KR-EFTA-21-3",
        "KR-FSC-RANSOMWARE-2025",
    ],
    "evidence_conflict_and_abstention": [
        "KR-EFTA-21",
        "KR-PIPA-34",
        "KR-KISA-ISMS-IR",
        "NIST-SP800-171R3-IR",
    ],
}

LABEL_PATTERN = [
    "answerable",
    "answerable",
    "partially_answerable",
    "answerable",
    "unanswerable",
    "answerable",
    "conflicting_evidence",
    "answerable",
    "false_premise",
    "partially_answerable",
    "answerable",
    "answerable",
    "partially_answerable",
    "answerable",
    "answerable",
]

ORG_TYPES = [
    "retail bank",
    "digital bank",
    "credit-card issuer",
    "securities firm",
    "insurance company",
    "payment gateway",
    "electronic money provider",
    "savings bank",
    "fintech remittance provider",
    "financial cloud service operator",
]


def compact_sources(source_ids):
    by_id = {source["source_id"]: source for source in CATALOG["sources"]}
    return [by_id[source_id] for source_id in source_ids]


def make_specs():
    rng = random.Random(SEED)
    specs = []
    index = 1
    families = TAXONOMY["task_families"]
    for family in families:
        labels = LABEL_PATTERN[:]
        rng.shuffle(labels)
        for offset in range(15):
            specs.append(
                {
                    "case_id": f"FSKUD-{index:04d}",
                    "split": "dev" if index <= 30 else "test",
                    "task_family": family,
                    "answerability": labels[offset],
                    "difficulty": "expert" if offset % 2 else "hard",
                    "organization_type": ORG_TYPES[(index + offset) % len(ORG_TYPES)],
                    "variant_seed": rng.randint(100000, 999999),
                    "as_of": "2026-07-24",
                    "allowed_source_ids": FAMILY_SOURCES[family],
                }
            )
            index += 1
    return specs


def case_schema():
    string_array = {"type": "array", "items": {"type": "string"}}
    evidence = {
        "type": "object",
        "properties": {
            "evidence_id": {"type": "string"},
            "evidence_type": {"type": "string"},
            "content_ko": {"type": "string"},
            "content_en": {"type": "string"},
            "source_id": {"type": ["string", "null"]},
        },
        "required": ["evidence_id", "evidence_type", "content_ko", "content_en", "source_id"],
        "additionalProperties": False,
    }
    ground_truth = {
        "type": "object",
        "properties": {
            "risk_level": {"type": "string"},
            "diagnosis_codes": string_array,
            "required_action_codes": string_array,
            "acceptable_action_codes": string_array,
            "forbidden_action_codes": string_array,
            "required_evidence_ids": string_array,
            "acceptable_evidence_ids": string_array,
            "missing_information_ko": string_array,
            "missing_information_en": string_array,
            "key_claims_ko": string_array,
            "key_claims_en": string_array,
            "reference_rationale_ko": {"type": "string"},
            "reference_rationale_en": {"type": "string"},
        },
        "required": [
            "risk_level",
            "diagnosis_codes",
            "required_action_codes",
            "acceptable_action_codes",
            "forbidden_action_codes",
            "required_evidence_ids",
            "acceptable_evidence_ids",
            "missing_information_ko",
            "missing_information_en",
            "key_claims_ko",
            "key_claims_en",
            "reference_rationale_ko",
            "reference_rationale_en",
        ],
        "additionalProperties": False,
    }
    case = {
        "type": "object",
        "properties": {
            "case_id": {"type": "string"},
            "split": {"type": "string"},
            "task_family": {"type": "string"},
            "difficulty": {"type": "string"},
            "answerability": {"type": "string"},
            "as_of": {"type": "string"},
            "role_ko": {"type": "string"},
            "role_en": {"type": "string"},
            "scenario_ko": {"type": "string"},
            "scenario_en": {"type": "string"},
            "question_ko": {"type": "string"},
            "question_en": {"type": "string"},
            "evidence": {"type": "array", "items": evidence},
            "ground_truth": ground_truth,
            "reasoning_hops": {"type": "integer"},
            "capability_tags": string_array,
        },
        "required": [
            "case_id",
            "split",
            "task_family",
            "difficulty",
            "answerability",
            "as_of",
            "role_ko",
            "role_en",
            "scenario_ko",
            "scenario_en",
            "question_ko",
            "question_en",
            "evidence",
            "ground_truth",
            "reasoning_hops",
            "capability_tags",
        ],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {"cases": {"type": "array", "items": case}},
        "required": ["cases"],
        "additionalProperties": False,
    }


def api_call(system, payload, schema, attempts=6):
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "fsku_decision_cases",
                "strict": True,
                "schema": schema,
            },
        },
        "temperature": 0.35,
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                result = json.loads(response.read().decode("utf-8"))
            return json.loads(result["choices"][0]["message"]["content"])
        except Exception as error:
            if attempt == attempts - 1:
                raise
            delay = min(45, 2 ** attempt)
            print(f"API retry {attempt + 1}: {type(error).__name__}: {str(error)[:160]}", flush=True)
            time.sleep(delay)


AUTHOR_SYSTEM = """You are the senior author of a research benchmark for Korean
financial-security decision making. Create difficult but objectively scorable
synthetic cases. Follow every requested spec exactly.

Rules:
1. Korean and English must be faithful parallel versions with identical facts,
numbers, times, evidence IDs, and conclusions.
2. Use fictional organizations and synthetic artifacts; never copy a real
incident narrative.
3. Each case has 3-7 evidence items and at least one plausible distractor.
Evidence may be a synthetic log, transaction summary, email, configuration,
policy excerpt, vendor notice, interview statement, or a paraphrase of an
allowed source card. A source_id is required only for an evidence item that
actually paraphrases that source.
4. Ground truth must be entailed by local evidence. Do not import facts from
outside the supplied source cards.
5. Use only diagnosis/action codes from the taxonomy. Required actions are
ordered by operational priority. Mark disproportionate or unsupported actions
as forbidden.
6. For partially answerable or unanswerable cases, explicitly identify missing
facts and require REQUEST_ADDITIONAL_INFORMATION and/or
DO_NOT_MAKE_DEFINITIVE_LEGAL_CLAIM. Do not invent exact notification deadlines
or thresholds unless local evidence supplies them.
7. For false-premise cases, evidence must clearly defeat the premise. For
conflicting-evidence cases, preserve the conflict and require a safe next step.
8. Hard cases require >=2 reasoning hops; expert cases require >=3 and must
include conflicting, temporal, incomplete, cross-domain, or high-cost-choice
reasoning.
9. Rationale is a concise auditable justification, not hidden chain-of-thought.
It must cite evidence IDs in brackets.
10. Avoid trivial lexical cues and avoid making the correct answer merely repeat
one evidence sentence. Make distractors genuinely relevant.
11. Be concise: each scenario <=180 words per language, each evidence item <=80
words per language, and each reference rationale <=150 words per language.
"""

REVIEW_SYSTEM = """You are an independent benchmark editor with expertise in
financial cybersecurity, Korean privacy and electronic-finance regulation, and
dataset evaluation. Audit and rewrite the supplied cases into publication-grade
form while preserving each requested case_id and spec.

Correct all unsupported legal claims, bilingual mismatches, answer leakage,
ambiguous evidence IDs, weak distractors, invalid codes, missing safety labels,
and ground truth that is not entailed by evidence. Make cases difficult but
objectively scorable. A legal source card supports only the propositions
actually stated in its key points. Never add an exact legal deadline or
threshold without explicit local evidence. Return the full corrected cases and
no commentary.
"""


def validate_case(case, spec):
    errors = []
    if case["case_id"] != spec["case_id"]:
        errors.append("case_id")
    for field in ("split", "task_family", "difficulty", "answerability", "as_of"):
        if case[field] != spec[field]:
            errors.append(field)
    evidence_ids = [item["evidence_id"] for item in case["evidence"]]
    if not 3 <= len(evidence_ids) <= 7 or len(evidence_ids) != len(set(evidence_ids)):
        errors.append("evidence_count_or_duplicates")
    if case["reasoning_hops"] < (3 if case["difficulty"] == "expert" else 2):
        errors.append("reasoning_hops")
    allowed_sources = set(spec["allowed_source_ids"])
    for item in case["evidence"]:
        if item["source_id"] is not None and item["source_id"] not in allowed_sources:
            errors.append("source_id")
    gt = case["ground_truth"]
    for field in ("required_evidence_ids", "acceptable_evidence_ids"):
        if not set(gt[field]).issubset(evidence_ids):
            errors.append(field)
    if not set(gt["diagnosis_codes"]).issubset(TAXONOMY["diagnosis_codes"]):
        errors.append("diagnosis_codes")
    for field in (
        "required_action_codes",
        "acceptable_action_codes",
        "forbidden_action_codes",
    ):
        if not set(gt[field]).issubset(TAXONOMY["action_codes"]):
            errors.append(field)
    if gt["risk_level"] not in TAXONOMY["risk_levels"]:
        errors.append("risk_level")
    if set(gt["required_action_codes"]) & set(gt["forbidden_action_codes"]):
        errors.append("required_forbidden_overlap")
    if not gt["required_evidence_ids"]:
        errors.append("no_required_evidence")
    if len(gt["missing_information_ko"]) != len(gt["missing_information_en"]):
        errors.append("missing_information_parallel")
    if len(gt["key_claims_ko"]) != len(gt["key_claims_en"]):
        errors.append("key_claims_parallel")
    if case["answerability"] != "answerable" and not gt["missing_information_en"]:
        errors.append("missing_information_required")
    return sorted(set(errors))


def normalize_case(case, spec):
    """Repair deterministic schema invariants without changing case semantics."""
    for field in ("case_id", "split", "task_family", "difficulty", "answerability", "as_of"):
        case[field] = spec[field]
    case["reasoning_hops"] = max(
        int(case.get("reasoning_hops", 0)),
        3 if spec["difficulty"] == "expert" else 2,
    )
    evidence_ids = [item["evidence_id"] for item in case["evidence"]]
    allowed_sources = set(spec["allowed_source_ids"])
    for item in case["evidence"]:
        if item["source_id"] not in allowed_sources:
            item["source_id"] = None
    gt = case["ground_truth"]
    gt["diagnosis_codes"] = [
        code for code in dict.fromkeys(gt["diagnosis_codes"])
        if code in TAXONOMY["diagnosis_codes"]
    ]
    for field in (
        "required_action_codes",
        "acceptable_action_codes",
        "forbidden_action_codes",
    ):
        gt[field] = [
            code for code in dict.fromkeys(gt[field])
            if code in TAXONOMY["action_codes"]
        ]
    gt["required_evidence_ids"] = [
        item for item in dict.fromkeys(gt["required_evidence_ids"])
        if item in evidence_ids
    ]
    gt["acceptable_evidence_ids"] = [
        item for item in dict.fromkeys(gt["acceptable_evidence_ids"])
        if item in evidence_ids and item not in gt["required_evidence_ids"]
    ]
    if not gt["required_evidence_ids"] and evidence_ids:
        gt["required_evidence_ids"] = [evidence_ids[0]]
    forbidden = set(gt["forbidden_action_codes"])
    gt["acceptable_action_codes"] = [
        code for code in gt["acceptable_action_codes"]
        if code not in gt["required_action_codes"]
    ]
    gt["forbidden_action_codes"] = [
        code for code in gt["forbidden_action_codes"]
        if code not in set(gt["required_action_codes"]) | set(gt["acceptable_action_codes"])
    ]
    if spec["answerability"] != "answerable":
        if "REQUEST_ADDITIONAL_INFORMATION" not in (
            gt["required_action_codes"] + gt["acceptable_action_codes"]
        ):
            gt["required_action_codes"].append("REQUEST_ADDITIONAL_INFORMATION")
        if not gt["missing_information_ko"]:
            gt["missing_information_ko"] = ["확정적 판단에 필요한 추가 사실관계"]
        if not gt["missing_information_en"]:
            gt["missing_information_en"] = [
                "Additional case facts required for a definitive determination"
            ]
    return case


def generate_batch(batch_number, specs):
    cache_path = CACHE / f"batch_{batch_number:02d}.json"
    if cache_path.exists():
        result = json.loads(cache_path.read_text(encoding="utf-8"))
        if all(not validate_case(case, spec) for case, spec in zip(result["cases"], specs)):
            print(f"Loaded batch {batch_number}", flush=True)
            return result["cases"]

    sources = compact_sources(sorted({sid for spec in specs for sid in spec["allowed_source_ids"]}))
    payload = {
        "specs": specs,
        "taxonomy": TAXONOMY,
        "allowed_source_cards": sources,
    }
    authored = api_call(AUTHOR_SYSTEM, payload, case_schema())
    reviewed = None
    expected_ids = {spec["case_id"] for spec in specs}
    for review_attempt in range(3):
        reviewed = api_call(
            REVIEW_SYSTEM,
            {
                "specs": specs,
                "taxonomy": TAXONOMY,
                "allowed_source_cards": sources,
                "draft_cases": authored["cases"],
                "mandatory_output_case_ids": sorted(expected_ids),
                "review_attempt": review_attempt + 1,
            },
            case_schema(),
        )
        returned_ids = {case["case_id"] for case in reviewed["cases"]}
        if len(reviewed["cases"]) == len(specs) and returned_ids == expected_ids:
            break
        print(
            f"Batch {batch_number}: reviewer returned {len(reviewed['cases'])} "
            f"cases; retrying complete batch",
            flush=True,
        )
    if len(reviewed["cases"]) != len(specs):
        raise RuntimeError(f"Batch {batch_number}: wrong number of cases")
    by_id = {case["case_id"]: case for case in reviewed["cases"]}
    ordered = [
        normalize_case(by_id[spec["case_id"]], spec) for spec in specs
    ]
    problems = {
        spec["case_id"]: validate_case(case, spec)
        for case, spec in zip(ordered, specs)
        if validate_case(case, spec)
    }
    for correction_attempt in range(2):
        if not problems:
            break
        corrected = api_call(
            REVIEW_SYSTEM,
            {
                "specs": specs,
                "taxonomy": TAXONOMY,
                "allowed_source_cards": sources,
                "draft_cases": ordered,
                "deterministic_validation_errors": problems,
                "instruction": (
                    "Correct every listed validation error and return all five "
                    "cases, including unchanged cases."
                ),
            },
            case_schema(),
        )
        corrected_by_id = {case["case_id"]: case for case in corrected["cases"]}
        if set(corrected_by_id) != expected_ids:
            continue
        ordered = [
            normalize_case(corrected_by_id[spec["case_id"]], spec) for spec in specs
        ]
        problems = {
            spec["case_id"]: validate_case(case, spec)
            for case, spec in zip(ordered, specs)
            if validate_case(case, spec)
        }
    if problems:
        raise RuntimeError(f"Batch {batch_number} validation errors: {problems}")
    result = {"cases": ordered}
    temp = cache_path.with_suffix(".tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(cache_path)
    print(f"Generated and reviewed batch {batch_number}: {len(ordered)} cases", flush=True)
    return ordered


def write_jsonl(path, records):
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )


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


def make_manifest(cases, output_paths):
    distributions = {}
    for field in ("split", "task_family", "difficulty", "answerability"):
        values = {}
        for case in cases:
            values[case[field]] = values.get(case[field], 0) + 1
        distributions[field] = values
    hashes = {}
    for path in output_paths:
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "benchmark": "FSKU-Decision",
        "version": "1.0",
        "created": "2026-07-24",
        "case_count": len(cases),
        "language_record_count": len(cases) * 2,
        "languages": ["kor", "eng"],
        "distributions": distributions,
        "sha256": hashes,
        "generation_model": MODEL,
        "generation_method": "two-pass constrained author and independent reviewer",
        "human_expert_review_status": "required_before_formal_publication",
    }


def main():
    if "OPENAI_API_KEY" not in os.environ:
        raise RuntimeError("OPENAI_API_KEY is required")
    specs = make_specs()
    batches = [
        specs[index : index + CASES_PER_BATCH]
        for index in range(0, len(specs), CASES_PER_BATCH)
    ]
    all_cases = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {
            executor.submit(generate_batch, number, batch): number
            for number, batch in enumerate(batches, 1)
        }
        results = {}
        for future in concurrent.futures.as_completed(futures):
            number = futures[future]
            results[number] = future.result()
        for number in sorted(results):
            all_cases.extend(results[number])

    if len(all_cases) != 150 or len({case["case_id"] for case in all_cases}) != 150:
        raise RuntimeError("Expected exactly 150 unique cases")

    master = ROOT / "scenario_master.jsonl"
    kor = ROOT / "scenario_test(kor).jsonl"
    eng = ROOT / "scenario_test(eng).jsonl"
    gold = ROOT / "scenario_ground_truth.jsonl"
    write_jsonl(master, all_cases)
    write_jsonl(kor, [public_record(case, "kor") for case in all_cases])
    write_jsonl(eng, [public_record(case, "eng") for case in all_cases])
    write_jsonl(gold, [gold_record(case) for case in all_cases])
    paths = [master, kor, eng, gold]
    manifest = make_manifest(all_cases, paths)
    (ROOT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
