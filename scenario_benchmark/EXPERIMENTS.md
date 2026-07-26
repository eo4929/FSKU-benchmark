# FSKU-Decision Pilot Experiment

## Configuration

- Model: `gpt-4.1-mini`
- Date: 2026-07-24
- Temperature: 0
- Setting: zero-shot, local evidence only
- Prompt: controlled diagnosis and action taxonomies from `scenario_baseline.py`
- Cases: all 150 Korean and all 150 English records

The result is a pipeline and difficulty sanity check, not a full model leaderboard.

## Automatic results

| Language | Overall | Hard | Expert |
|---|---:|---:|---:|
| English | 73.84 | 80.31 | 63.58 |
| Korean | 72.94 | 79.25 | 62.94 |

The overall score is the unweighted mean of answerability accuracy, diagnosis
F1, action quality, and evidence F1. Risk, missing-information, schema, and
safety results are diagnostic metrics rather than weighted score components.

### English answerability slices

| Slice | Score |
|---|---:|
| Answerable | 82.27 |
| Partially answerable | 71.43 |
| Unanswerable | 55.04 |
| False premise | 56.63 |
| Conflicting evidence | 41.30 |

### Korean answerability slices

| Slice | Score |
|---|---:|
| Answerable | 82.11 |
| Partially answerable | 66.32 |
| Unanswerable | 55.46 |
| False premise | 60.30 |
| Conflicting evidence | 40.42 |

## Safety diagnostics

The safety violation rate is 24.67\% for English and 29.33\% for Korean. The
baseline selected at least one explicitly forbidden action in 36 English cases
and 40 Korean cases. It made an unsupported definitive notification or
authority-reporting choice in 6 English cases and 14 Korean cases. These errors
are reported separately so they cannot be obscured by stronger scores on other
components.

## Cross-lingual consistency

| Component | Consistency |
|---|---:|
| Overall | 84.53 |
| Answerability | 93.33 |
| Risk | 78.67 |
| Diagnosis | 77.37 |
| Actions | 75.13 |
| Evidence selection | 98.14 |

The high evidence overlap but substantially lower diagnosis and action
consistency suggests that models often read the same evidence in both languages
yet reach different operational decisions.

## Interpretation

The pilot confirms three desired benchmark properties:

1. the task is not saturated by a capable compact model;
2. structurally calibrated expert cases are materially harder than hard cases;
3. uncertainty, conflicting evidence, and safe action selection are the main
failure modes.

A publication should evaluate additional closed and open models, report
bootstrap confidence intervals, and conduct the human evaluation protocol in
`HUMAN_EVALUATION.md`.
