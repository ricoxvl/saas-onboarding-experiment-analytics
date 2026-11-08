# Phase 2 | Experiment analysis and product decision guide

This is a **fictional SaaS product case study** using deterministic synthetic data. Do not interpret the simulated experiment as a real company A/B test or claim a verified retention increase on a resume.

## 1. What question are we deciding?

Would a guided onboarding experience increase **day-28 returning users** enough to justify a rollout, without creating unacceptable user friction?

- **Control:** standard onboarding
- **Treatment:** guided onboarding
- **Unit:** assigned user, not event or workspace
- **Primary metric:** whether the randomized user is active exactly 28 days after signup
- **Denominator:** every randomized user (intention-to-treat)
- **Secondary metric:** activated within D7 = workspace created AND integration connected
- **Negative guardrails:** any onboarding error by D7; any support ticket by D7

A returned user counts *once*, and non-returning users remain in the denominator. D28 is an exact-day metric, **not** rolling 28-day retention.

## 2. Sample-ratio mismatch and data audit

Before interpreting outcomes, the pipeline checks:

1. Each user has an allowed experiment assignment and a valid cohort month.
2. Every user has exactly one signup event.
3. Event-to-user references are valid; flag columns match observed events.
4. Funnel steps are logically ordered (integration requires workspace; invitation requires integration).
5. Event times are within their declared observation windows.
6. Event types are recognized, with no duplicate user-event combinations.
7. 50/50 sample allocation is assessed with a chi-square SRM test (flag threshold: p < 0.001).
8. Team/solo share imbalance is reported using standardized mean differences (absolute > 0.1 is a descriptive prompt to inspect).

A failed **event-level quality audit stops analysis**. The SRM flag is reported separately and requires investigation; a low SRM p-value undermines trust in the results. Assignment balance measures are diagnostics, not standalone causal proof.

## 3. Treatment effect and uncertainty

The analysis reports treatment minus control as:

- Percentage-point difference in return rate.
- Relative percentage change from the control rate.
- 95% unpooled Wald interval for the percentage-point difference.
- Two-sided pooled two-proportion z-test p-value.

These normal-approximation methods are for learning and large-enough samples, not for tiny cohorts or extreme probabilities. An effect being significant at 0.05 does **not** automatically make it economically meaningful.

A helpful reading pattern:

- Is the data valid and is allocation credible?
- Is the primary estimate positive, and what values are compatible with its confidence interval?
- What is the smallest improvement worth shipping for the hypothetical business?
- Does the treatment introduce unacceptable errors or support load?
- Is the sample sufficiently sensitive to practical effects?

## 4. Guardrail interpretation

The generator intentionally models **more onboarding errors in treatment** (10% vs 8% probability) to create a benefit-risk tradeoff, rather than an unrealistic treatment that wins every metric.

- For errors and tickets, **positive** treatment-control lift is **worse**.
- The example risk tolerance is **+2 percentage points** on each guardrail.
- `upper_95_ci_below_risk_limit` is true only if the guardrail's *upper* 95% bound falls below that threshold.
- Failure to reject a null hypothesis does **not** prove the change is safe; an upper bound above the threshold means harmful increases have not been ruled out.

The guardrail tolerance is an **illustrative teaching rule**, not an actual company's pre-registered release policy. Guardrail confidence intervals are unadjusted, so joint safety coverage is not guaranteed.

## 5. Subgroups, cohorts, and multiplicity

`segments.csv` reports treatment-control day-28 retention effects for **team**, **solo**, and each **signup-month cohort**.

These are exploratory, not powered subgroup experiments. The pipeline calculates Benjamini-Hochberg FDR q-values **across all of these retention subgroup contrasts as a single family**. A subgroup looking different from zero does not establish that the treatment works *differently* between groups; that claim requires an interaction test and separate study design.

No demographic or sensitive user attributes are simulated.

## 6. Prospective experiment sizing

`planning_sensitivity` reports approximate balanced two-proportion sample sizes to detect **+2, +3 and +5 percentage-point** increases at 5% two-sided alpha and 80% power. It also shows an MDE given the **smaller observed arm size**, as a conservative approximation.

It uses the observed synthetic control rate only as a **reference planning baseline**. These values should not be described as post-hoc achieved power or proof that this experiment was adequately designed.

A live experiment should define its business minimum effect, baselines, desired power, allowed run time, eligibility, data delay, and stopping rule **before launch**.

## 7. Where to find the reproducible outputs

Run:

```bash
python -m saas_analytics.simulate --users 4000 --seed 42
python -m saas_analytics.analyze
python -m unittest discover -s tests -v
```

Inspect:

- `reports/generated/quality_checks.json`: event integrity checks
- `reports/generated/experiment_results.json`: primary/secondary effects, guardrails, allocation checks, sample sizing, segmented results
- `reports/generated/segments.csv`: exploratory segment contrasts and FDR q-values
- `reports/generated/funnel.csv`: onboarding journey and guardrail counts
- `reports/generated/cohorts.csv`: month-specific retention and activation
- `reports/generated/summary.md`: narrative interpretation

Generated reports are excluded from Git history but are reproducible with the commands above.

## 8. Portfolio-ready description (accurate and defensible)

> Built a reproducible SaaS onboarding experimentation case study with simulated event-level data, SQL funnels/cohorts, two-proportion inference, FDR-adjusted subgroup analysis, guardrail monitoring, power/MDE planning, and automated data-quality checks.

**Never** represent the synthetic model's output as real retention improvement, production adoption, or a deployed customer experiment.
