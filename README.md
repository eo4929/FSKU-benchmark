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

## Benchmark Structure

FSKU is hierarchically organized into 4 main domains and 12 sub-domains, allowing for a multi-faceted analysis of a model's performance and the identification of its weaknesses.

| Main Domain                  | Sub-domain (Data Ratio)                                                                                                                                              | Main Sources  |
| :--------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------ |
| **General Financial Security** | Financial Business (5.0%)<br>Security Governance (5.0%)<br>Electronic Security (5.0%)<br>Privacy (5.0%)                                                              | (Undisclosed) |
| **Finance IT Security** | General IT Security (8.0%)<br>Advanced IT Security (12.0%)                                                                                                            | (Undisclosed) |
| **Finance Legal & Regulation** | Electronic Finance (12.0%)<br>Telecommunications (12.0%)<br>Privacy Law (12.0%)<br>Digital Signature (7.0%)<br>Credit Information (12.0%)                                | (Undisclosed) |
| **Emerging Trends** | Financial Security Trends (5.0%)                                                                                                                                     | (Undisclosed) |

*To ensure the fairness of the competition, the main sources will be disclosed after the 2025 Financial AI Challenge.*

![FSKU Domains](.images/overview_FSKU.png)
*Figure: FSKU Domain and Sub-domain Structure*

## Dataset Example

Each item consists of a question, four options, the correct answer, and a detailed explanation.

| Item        | Content                                                                                                                                                              |
| :---------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Domain** | Finance legal & regulation                                                                                                                                           |
| **Sub-domain** | Electronic finance                                                                                                                                                   |
| **Question** | What information must be included in the certificate that a designated authority issues to an accredited digital signature service provider?                         |
| **Options** | (1) Evaluation results and compliance with operational standards<br>(2) Scope and validity period of the accreditation<br>(3) Financial condition of the provider<br>(4) Number of clients served by the provider |
| **Answer** | (2) Scope and validity period of the accreditation                                                                                                                   |
| **Explanation** | According to Article 9 of the Digital Signature Act, when a designated authority confirms that a provider complies with operational standards, it must issue a certificate that includes the scope and validity period of the accreditation. |
| **Reference** | Digital Signature Act, Article 9                                                                                                                                     |
## Leaderboard

The following are the results from an evaluation of 11 representative LLMs. The findings indicate that models generally struggle with the legal and regulatory domains.

The chart below shows the average accuracy across all 11 LLMs for each sub-domain, illustrating the overall difficulty landscape of the benchmark.

![FSKU Sub-domain Average Accuracy](https://i.imgur.com/tL4H9vG.png)

| Model | Overall Accuracy | Finance Legal & Regulation | Finance IT Security |
| :--- | :---: | :---: | :---: |
| **claude-4** | (Undisclosed) | (Undisclosed) | (Undisclosed) |
| gpt-4.1 | (Undisclosed) | (Undisclosed) | (Undisclosed) |
| ... | ... | ... | ... |

*To ensure the fairness of the competition, detailed scores will be disclosed after the 2025 Financial AI Challenge.*

## Evaluation Method

Models are evaluated in a zero-shot setting without fine-tuning. As all questions are multiple-choice with four options, accuracy is measured by extracting the first numerical token from the model's response and comparing it to the correct answer.

### Running the Evaluation Script (Example)

```python
python evaluate.py \
    --model_name "gpt-4.1" \
    --data_path "./data/fsku_test.csv" \
    --output_dir "./results"