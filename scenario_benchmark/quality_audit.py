"""Independent semantic audit of every FSKU-Decision case."""

import concurrent.futures
import json
import os
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL = os.environ.get("FSKU_AUDIT_MODEL", "gpt-4.1-mini")
BATCH_SIZE = 5
WORKERS = 2


def load_jsonl(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def schema():
    score = {"type": "integer", "minimum": 1, "maximum": 5}
    audit = {
        "type": "object",
        "properties": {
            "case_id": {"type": "string"},
            "bilingual_fidelity": score,
            "evidence_grounding": score,
            "operational_safety": score,
            "legal_fidelity": score,
            "difficulty_quality": score,
            "critical_issues": {"type": "array", "items": {"type": "string"}},
            "minor_issues": {"type": "array", "items": {"type": "string"}},
            "verdict": {"type": "string", "enum": ["pass", "revise"]},
        },
        "required": [
            "case_id",
            "bilingual_fidelity",
            "evidence_grounding",
            "operational_safety",
            "legal_fidelity",
            "difficulty_quality",
            "critical_issues",
            "minor_issues",
            "verdict",
        ],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {"audits": {"type": "array", "items": audit}},
        "required": ["audits"],
        "additionalProperties": False,
    }


SYSTEM = """You are an independent quality auditor for a publication-grade
financial cybersecurity benchmark. Audit, do not rewrite. Assess each case only
from its local evidence and supplied official-source key points.

Scores:
5 = publication quality; 4 = sound with a minor issue; 3 = material issue needing
revision; 2 = major flaw; 1 = unusable.

Check:
- Korean-English versions preserve identical facts, numbers, times, and scope.
Equivalent units such as 2억 원 and KRW 200 million are equal, not mismatches.
- Every diagnosis, required action, risk level, and reference-rationale claim is
entailed by local evidence. A plausible inference must be labeled as such.
- Required action order is safe and operationally realistic; evidence is
preserved before destructive remediation; uncertainty does not prevent
proportionate containment or escalation.
- Legal claims do not invent deadlines, thresholds, or mandatory duties absent
from the local source cards.
- The case genuinely requires at least the declared reasoning hops and contains
a relevant distractor without answer leakage.

Set verdict=revise if any dimension is <=3 or any critical issue exists. Be
specific and concise. Return exactly one audit per requested case ID.
"""


def call_api(payload):
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "fsku_quality_audit",
                "strict": True,
                "schema": schema(),
            },
        },
        "temperature": 0,
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
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                result = json.loads(response.read().decode("utf-8"))
            return json.loads(result["choices"][0]["message"]["content"])
        except Exception:
            if attempt == 5:
                raise
            time.sleep(min(30, 2 ** attempt))


def audit_batch(number, cases, source_cards):
    path = ROOT / ".generation_cache" / f"audit_{number:02d}.json"
    expected = {case["case_id"] for case in cases}
    if path.exists():
        cached = json.loads(path.read_text(encoding="utf-8"))
        if {item["case_id"] for item in cached["audits"]} == expected:
            print(f"Loaded audit {number}", flush=True)
            return cached["audits"]
    used_sources = {
        item["source_id"]
        for case in cases
        for item in case["evidence"]
        if item["source_id"]
    }
    payload = {
        "required_case_ids": sorted(expected),
        "source_cards": [
            source for source in source_cards if source["source_id"] in used_sources
        ],
        "cases": cases,
    }
    result = call_api(payload)
    returned = {item["case_id"] for item in result["audits"]}
    if returned != expected:
        raise RuntimeError(f"Audit batch {number} ID mismatch")
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Audited batch {number}: {len(cases)} cases", flush=True)
    return result["audits"]


def main():
    cases = load_jsonl(ROOT / "scenario_master.jsonl")
    source_cards = json.loads(
        (ROOT / "source_catalog.json").read_text(encoding="utf-8")
    )["sources"]
    batches = [
        cases[index : index + BATCH_SIZE]
        for index in range(0, len(cases), BATCH_SIZE)
    ]
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {
            executor.submit(audit_batch, number, batch, source_cards): number
            for number, batch in enumerate(batches, 1)
        }
        for future in concurrent.futures.as_completed(futures):
            number = futures[future]
            results[number] = future.result()
    audits = [
        audit for number in sorted(results) for audit in results[number]
    ]
    revised = [audit for audit in audits if audit["verdict"] == "revise"]
    report = {
        "model": MODEL,
        "case_count": len(audits),
        "pass_count": len(audits) - len(revised),
        "revise_count": len(revised),
        "mean_scores": {
            field: round(sum(item[field] for item in audits) / len(audits), 3)
            for field in (
                "bilingual_fidelity",
                "evidence_grounding",
                "operational_safety",
                "legal_fidelity",
                "difficulty_quality",
            )
        },
        "audits": audits,
    }
    (ROOT / "quality_audit_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in report.items() if key != "audits"}, indent=2))


if __name__ == "__main__":
    main()
