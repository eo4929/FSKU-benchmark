# FSKU-Decision: Scenario-Based Financial Security Decision Benchmark

FSKU-Decision extends FSKU beyond knowledge recall. It evaluates whether a model can diagnose a financial-security situation, distinguish known facts from uncertainty, prioritize defensible actions, and cite the evidence that supports each conclusion.

## Benchmark unit

Each bilingual case contains:

- a role and operational objective;
- a time-anchored scenario;
- three to seven local evidence items such as logs, alerts, policy excerpts, vendor notices, transaction summaries, or regulatory evidence cards;
- an explicit response schema;
- private ground truth containing answerability, diagnosis, risk, ordered actions, required citations, missing information, forbidden claims/actions, and a reference rationale.

The Korean and English records share the same `case_id`, labels, evidence IDs, and ground truth. They are parallel evaluation forms, not separate cases.

## Capability matrix

| Capability | What is tested |
|---|---|
| Incident triage | Separating indicators from conclusions and choosing proportionate containment |
| Multi-hop reasoning | Combining technical, operational, legal, and policy evidence |
| Evidence grounding | Citing the local evidence that entails a diagnosis or action |
| Decision quality | Selecting and prioritizing actions under operational constraints |
| Legal caution | Distinguishing a duty to assess from a conclusively established reporting duty |
| Abstention | Requesting missing facts or rejecting a false premise |
| Safety | Avoiding destructive, privacy-invasive, or unsupported actions |
| Cross-lingual consistency | Producing equivalent decisions in Korean and English |

## Difficulty

Every case is tagged `hard` or `expert`. A hard case requires at least two reasoning hops and contains a plausible distractor. An expert case has at least four hops, or combines at least three hops with partial answerability, or tests unanswerability, a false premise, or conflicting evidence. The labels were checked against a pilot baseline after construction.

## Required model output

Predictions use JSON:

```json
{
  "case_id": "FSKUD-0001",
  "answerability": "partially_answerable",
  "risk_level": "high",
  "diagnosis_codes": ["ACCOUNT_TAKEOVER"],
  "action_codes": [
    "PRESERVE_EVIDENCE",
    "REVOKE_SESSIONS",
    "ENFORCE_STEP_UP_AUTH",
    "REQUEST_ADDITIONAL_INFORMATION"
  ],
  "evidence_ids": ["E1", "E3", "E5"],
  "missing_information": ["Whether the challenged transactions were customer-authorized"],
  "rationale": "..."
}
```

Models may explain their reasoning, but they must not provide hidden chain-of-thought. The rationale should be a concise decision justification tied to evidence.

## Data splits

- `dev`: 30 cases with public ground truth for prompt and system development.
- `test`: 120 cases. Inputs are public; ground truth is maintained separately.
- Total: 150 unique bilingual cases / 300 language-specific records.
- Difficulty after structural calibration: 92 hard and 58 expert cases.

The benchmark reports results separately for Korean and English. A bilingual consistency score is also reported for models evaluated on both.

## Automatic evaluation

The primary score is the unweighted mean of four normalized components,
reported on a 0--100 scale:

| Primary component | Metric |
|---|---|
| Answerability | Accuracy |
| Diagnosis | F1 |
| Action quality | Mean of action-set F1 and order-aware nDCG |
| Evidence grounding | Evidence-citation F1 |

Risk accuracy, missing-information coverage, JSON validity, and safety violation
rate are reported separately as diagnostic metrics. Safety violations include
explicitly forbidden actions and unsupported definitive legal actions. They
are not folded into the primary score because unsafe behavior should not be
obscured by gains on other components.

## Human score

For a publication-quality evaluation, two financial-security reviewers independently grade a stratified sample on:

1. factual and legal correctness;
2. evidence faithfulness;
3. prioritization and operational feasibility;
4. uncertainty calibration;
5. completeness without unsafe overreach.

Each dimension uses a 1–5 anchored rubric. Disagreements of two or more points are adjudicated by a third reviewer. Report weighted Cohen's kappa or Krippendorff's alpha and bootstrap confidence intervals.

## Ground-truth policy

Ground truth distinguishes:

- `required`: essential for a fully correct answer;
- `acceptable`: valid but not essential;
- `forbidden`: contradicted, disproportionate, destructive, or unsupported;
- `missing_information`: facts necessary for a more definitive conclusion.

Legal evidence is time-anchored. A case must not infer an exact statutory deadline or threshold unless the local evidence provides the applicable rule and the triggering facts.

## Contamination controls

- Generate cases from compositional templates and synthetic organizations; do not copy real incident narratives.
- Keep final test ground truth separate from input files.
- Record creation date, source versions, and hashes.
- Release future test refreshes with new artifact values and changed evidence combinations.
- Evaluate near-duplicate overlap across splits before release.

## Limitations

The dataset is a research benchmark, not legal advice. Machine-assisted drafts and translations require domain-expert review before a formal public release. Automatic scores emphasize reproducibility but do not replace expert evaluation of nuanced narrative quality.
