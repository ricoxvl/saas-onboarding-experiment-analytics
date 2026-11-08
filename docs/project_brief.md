# Project brief

## Context
A fictional B2B SaaS business sees user drop-off between signup, workspace creation, integration connection, and return usage.

## Decision
Should the product team replace a standard onboarding experience with a guided onboarding flow?

## Hypothesis
Guided onboarding may increase day-28 return activity. This is a hypothetical experiment; the pipeline uses **synthetically simulated behavior**, not observed customer outcomes.

## Experimental plan
- **Unit of randomization and analysis:** unique new user
- **Arms:** standard flow (control) vs guided flow (treatment), 50/50 random assignment
- **Primary metric:** user returned on signup day +28 (binary); denominator = all randomized users
- **Supporting metric:** activation within seven days, defined as workspace creation AND integration connection within seven days
- **Negative-outcome guardrails:** at least one onboarding error by D7 and at least one support ticket by D7; lower is better, among all assigned users
- **Illustrative risk tolerance:** +2 percentage points on either negative-outcome guardrail. This threshold is pedagogical and is not a pre-registered rule from a real business.
- **Exploratory cuts:** solo vs team users and signup month, clearly marked exploratory
- **SRM check:** chi-square test against 50/50, flag when p < 0.001
- **Effect measure:** absolute difference in binary rates (treatment - control), with 95% CI and two-sided z-test
- **Multiple comparisons:** one predesignated primary retention contrast; exploratory retention subgroups receive Benjamini-Hochberg FDR adjustment across team/solo + month contrasts. Guardrails receive unadjusted descriptive CIs and are not confirmatory efficacy tests.
- **Sizing:** approximate balanced two-proportion n per group and MDE at 80% target power, 5% two-sided alpha, with normal-approximation formulas.
- **Decision principles:** assess business significance and interval uncertainty alongside p-value; review onboarding guardrails and segment heterogeneity before any actual rollout decision.

## Simulation assumptions
- 4,000 default users; seeded pseudo-random assignment and outcomes.
- Users sign up during a 90-day window starting January 1, 2026.
- Fictional treatment users are configured with moderately higher completion and return probabilities. They are also assigned a higher onboarding-error probability (10% vs 8% control), intentionally introducing a possible benefit-risk tradeoff.
- Fictional support tickets occur with a 3.5% base chance plus 10 percentage points among users with onboarding errors.
- Return probabilities depend on assignment, activation, and team/solo segment; such a model embeds assumptions, **not** empirical causality.
- Outcomes are generated fully matured. A live trial would need observation windows, censoring checks, instrumentation QA, privacy safeguards, and a pre-registered stopping rule.
- The modeled data-generating probabilities are assumptions, not inferred treatment effects or a measure of external validity.
- Experiment results are **intention-to-treat**: all users remain in the denominator of the group to which they were randomized.

## Future deliverables
Dashboard, segment uncertainty, power/MDE sensitivity, and a final decision memo using transparent simulated results.
