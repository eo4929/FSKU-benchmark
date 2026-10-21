# FSKU: A Benchmark for Financial Security Knowledge Understanding

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**FSKU** is a novel Question-Answering (QA) benchmark designed to measure how well Large Language Models (LLMs) understand the practical, domain-specific knowledge required in the financial security landscape.


## Dataset Structure

FSKU provides three task types in both Korean and English:

```
FSKU-benchmark/
├── Multiple-Choice Questions
│   ├── test(kor).csv              # Korean 
│   ├── test(eng).csv              # English 
│   └── answer.csv                 # Answer key (numeric only)
│
├── Subjective Questions
│   ├── subjective_test(kor).csv   # Korean 
│   └── subjective_test(eng).csv   # English 
│
├── Scenario Decision Questions
│   ├── scenario_benchmark/scenario_test(kor).jsonl
│   ├── scenario_benchmark/scenario_test(eng).jsonl
│   ├── scenario_benchmark/scenario_ground_truth.jsonl
│   ├── scenario_benchmark/source_catalog.json
│   └── scenario_benchmark/manifest.json
│
├── Code
│   ├── baseline.py                # Baseline inference script
│   ├── evaluate.py                # Evaluation script
│   ├── scenario_evaluate.py       # Scenario decision evaluator
│   ├── scenario_consistency.py    # Korean-English consistency evaluator
│   └── categories.py              # Category definitions
│
└── Documentation
    ├── README.md
    ├── LICENSE
    └── images/
```
