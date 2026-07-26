# FSKU-Decision Human Evaluation Protocol

Automatic scoring is the primary reproducible metric. Human review evaluates the quality of the concise rationale and detects errors not represented by the controlled labels.

## Reviewers

- At least two independent reviewers with financial cybersecurity, financial IT audit, privacy, or electronic-finance regulatory experience.
- Reviewers must not see model identity.
- A third reviewer adjudicates any dimension with a difference of two or more points.

## Five dimensions

### 1. Factual and legal correctness

- **1:** Materially false; recommends an illegal or clearly unsafe course.
- **2:** Major error affecting the decision.
- **3:** Core decision is defensible but contains a non-trivial omission or imprecision.
- **4:** Correct with only a minor qualification missing.
- **5:** Fully correct and appropriately qualified for the case date and evidence.

### 2. Evidence faithfulness

- **1:** Conclusions contradict or fabricate evidence.
- **2:** Several central claims are unsupported.
- **3:** Main conclusion is grounded, but one material claim lacks support.
- **4:** Claims are grounded with minor citation imprecision.
- **5:** Every material claim is traceable to the cited local evidence.

### 3. Prioritization and operational feasibility

- **1:** Actions would worsen the incident or destroy evidence.
- **2:** Ordering is unsafe or operationally unrealistic.
- **3:** Actions are broadly useful but prioritization is incomplete.
- **4:** Sound and feasible ordering with a minor gap.
- **5:** Proportionate, time-sensitive, and dependency-aware prioritization.

### 4. Uncertainty calibration

- **1:** Fabricates certainty or refuses despite decisive evidence.
- **2:** Serious overclaim or over-refusal.
- **3:** Recognizes uncertainty but fails to identify a key missing fact.
- **4:** Appropriate confidence with a minor calibration issue.
- **5:** Precisely separates facts, inferences, unresolved questions, and safe next steps.

### 5. Completeness without unsafe overreach

- **1:** Misses the core response or adds dangerous actions.
- **2:** Multiple essential elements missing or unsupported.
- **3:** Covers the main decision with one substantial omission.
- **4:** Complete apart from a minor useful element.
- **5:** Covers diagnosis, immediate actions, evidence, obligations, and missing facts without overreach.

## Sampling

For the main paper, review all cases if feasible. At minimum, use a stratified sample containing:

- at least 10 cases from every task family;
- all answerability labels;
- equal Korean and English outputs;
- equal hard and expert cases;
- every evaluated model family.

## Reporting

Report the mean and 95% bootstrap confidence interval for each dimension. Report weighted Cohen's kappa for two reviewers or Krippendorff's alpha for more than two. Also report the percentage of outputs containing a critical safety error, fabricated citation, unsupported reporting claim, and over-refusal.
