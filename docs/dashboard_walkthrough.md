# Dashboard walkthrough — reviewer and portfolio guide

The interactive dashboard lives in [`dashboard/app.py`](../dashboard/app.py) and is built with Streamlit, Plotly, Pandas, Python, and SQLite.

**Important:** The dataset is **entirely synthetic**. It is generated from fixed fictional probabilities, including a deliberately elevated onboarding-error probability in the treatment arm. Do not claim that these results were observed in production.

## Start the dashboard

```bash
git clone https://github.com/ricoxvl/saas-onboarding-experiment-analytics.git
cd saas-onboarding-experiment-analytics
python -m pip install -r requirements.txt
streamlit run dashboard/app.py
```

The dashboard generates and validates its own seeded demo SQLite database on first launch. The full analysis CLI is independent:

```bash
python -m saas_analytics.simulate --users 4000 --seed 42
python -m saas_analytics.analyze
```

## Suggested 3-minute demonstration

**1. Overview — identify the problem.** Start with signup volume, seven-day activation, day-28 return activity and onboarding-error exposure. Compare the retention trend for the standard and guided onboarding experiences. Explain that the key question is not just whether users complete initial setup, but whether they return 28 days later.

**2. Onboarding funnel — locate friction.** Inspect the four monotonic stages (signup, workspace created, integration connected, D7 activated). Compare counts and percentages for each randomized arm. Teammate invitations are intentionally excluded: not every signup is eligible or needs to invite a colleague.

**3. Retention & cohorts — examine stability.** Toggle the chart between D28 retention and D7 activation. Review each signup-month cohort and the exploratory team/solo comparisons. Explain that BH-adjusted q-values account for testing several displayed subgroup retention contrasts; a subgroup-specific p-value does not itself test heterogeneous treatment effects.

**4. Experiment lab — make a careful decision.** Review the treatment-minus-control percentage-point change, the 95% confidence interval, the two-sided p-value, and sample allocation. Inspect the plotted intervals for the primary and secondary outcomes. Adjust the **illustrative** guardrail tolerance to see how much harmful increase remains compatible with the data. Discuss sample-size planning and why failing to reject a guardrail null is not proof of safety.

## Interactive controls

- **Synthetic seed:** generates a new seeded hypothetical scenario; 42 is the default. Repeatedly trying seeds for an appealing result would be selection bias, not valid experimentation.
- **Number of users:** generates 2,000, 4,000, or 8,000 simulated users to explore how uncertainty changes with sample size. Changing sample size after inspecting p-values is not an acceptable live-experiment stopping policy.
- **Segment:** limits analysis to solo or team signup users. The segment is measured before exposure and is therefore appropriate for exploratory slicing.
- **Signup cohorts:** selects signup months. These filters do not use outcome data.
- **Export CSV:** downloads only the selected **synthetic user rows**, so analytics can be reproduced elsewhere.
- **Guardrail tolerance:** changes a demonstration threshold; it is not a pre-registered launch criterion.

## Definitions

| Measure | User-level definition | Interpretation |
| --- | --- | --- |
| Signups | Number of randomized new users | Allocation denominator |
| D7 activation | Workspace created and integration connected within D7 | More is better |
| D28 retention | Activity recorded on **day 28** after signup | More is better; exact day, not rolling 28-day activity |
| Onboarding errors | At least one onboarding error within D7 | Less is better |
| Support tickets | At least one support ticket within D7 | Less is better |
| Relative lift | (Treatment rate − control rate) / control rate | Do not confuse with percentage-point difference |
| Confidence interval | Unpooled normal-approximation 95% interval for the rate difference | Not a probability that a fixed effect varies |
| SRM p-value | Chi-square test of 50/50 user assignment | A severe imbalance can cast doubt on validity |
| MDE | Prospective two-proportion planning approximation at 80% power | Not achieved/observed power |

## Quality and reproducibility

The dashboard refuses to load a database if event-level validation fails. The test suite checks data filtering, monotonic funnels, agreement with the analytical CLI, cohort totals, and corruption detection. A Streamlit smoke test navigates all four views.

```bash
python -m unittest discover -s tests -v
```

Continuous integration also regenerates the source dataset, runs the analysis and uploads synthetic report artifacts. The source and test code are in this public repository.

## Deploying the dashboard

Use Streamlit Community Cloud with repository `ricoxvl/saas-onboarding-experiment-analytics`, branch `main`, and entry point `dashboard/app.py`. The root `requirements.txt` supplies dashboard packages and editable installation of the analytics library. The demo does not need API keys or customer data.

After deploying, verify that the synthetic-data disclaimer remains prominent, every view loads, and the sidebar filters recalculate the results. Add the resulting **actual deployment URL** to this README only after you have deployed the app.

## Interview explanation (accurate)

> I built a complete synthetic SaaS product analytics case study to demonstrate how I would evaluate an onboarding redesign. I generated reproducible event-level data, implemented SQL funnel and cohort metrics, then built an interactive dashboard for retention, activation, randomization diagnostics, statistical uncertainty, guardrail tradeoffs and experiment sizing. Automated QA stops analysis when the underlying events are inconsistent.

Avoid saying the simulation improved actual customer retention or that it was an independently run production A/B experiment. It wasn't.
