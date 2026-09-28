# FSKU: A Benchmark for Financial Security Knowledge Understanding

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**FSKU** is a novel Question-Answering (QA) benchmark designed to measure how well Large Language Models (LLMs) understand the practical, domain-specific knowledge required in the South Korean financial security landscape.

> ### Important Notice
>
> The FSKU benchmark and its related data will be used as an official task for the **2025 Financial AI Challenge (August 1 - August 29, 2025)**.
> [Challenge Page](https://www.fsec.or.kr/bbs/detail?menuNo=66&bbsNo=11704)
>
> Therefore, to ensure the fairness of the competition, detailed information about the benchmark, the full dataset, and the leaderboard scores will be **released after the competition period**.

## Overview

While recent LLMs have demonstrated remarkable capabilities, their proficiency in high-stakes domains like financial security—which requires high reliability for tasks such as fraud detection and regulatory compliance—remains under-explored. As seen in real-world failure cases at the Financial Security Institute (FSI) of South Korea, LLMs can often produce responses that are fluent but factually incorrect, posing significant risks in financial applications.

FSKU was created to address this gap. Based on authoritative sources such as official financial certification textbooks, laws, and supervisory guidelines, FSKU systematically evaluates whether LLMs possess the knowledge required for real-world tasks within financial institutions.

## Features of FSKU

* **Domain-Specific**: FSKU is the first benchmark to focus specifically on financial 'security,' including governance, IT security, regulatory compliance, and emerging threats, rather than general financial knowledge.
* **Grounded in Practice**: The benchmark is highly relevant to industry practice, as it is based on the curriculum of official national certifications like the Financial Security Manager (FSM) and actual laws (e.g., Electronic Financial Transactions Act, Credit Information Use and Protection Act).
* **Rigorous Quality Control**: Drafts were generated using a combination of real-world professional financial security documents and an LLM (GPT-4o). These drafts were then validated and revised by experts from the Financial Security Institute against eight quality criteria to ensure their reliability and validity.
* **Bilingual Support**: All data is provided in both Korean and English, making it accessible to researchers worldwide.
* **Three Complementary Tasks**: FSKU evaluates multiple-choice knowledge, short-form explanation, and evidence-grounded scenario decision making.

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
